"""Reproducible EfficientNetB0 retraining without modifying the source dataset.

Use Python -I -B. See --help. Stages: prepare -> audit -> train -> finalize.
A one-shot final-test lock freezes the candidate and validation-selected threshold.
No stage promotes a model automatically. Original model + threshold are backed up.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import ctypes
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import math
from types import SimpleNamespace
import os
from pathlib import Path
import platform
import shutil
import sys
import time
import traceback

# Imports resolve only from project-owned tools, never from the dataset.
spec = importlib.util.spec_from_file_location("retraining_metrics", Path(__file__).with_name("retraining_metrics.py"))
rm = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rm
spec.loader.exec_module(rm)
BACKEND = Path(__file__).resolve().parents[1]
ORIGINAL_MODEL = BACKEND / "model" / "deepfake_model.keras"
ORIGINAL_THRESHOLD = BACKEND / "model" / "threshold.json"
CURRENT_RUN = None  # Set only after ownership/location validation, never from raw CLI input.


def safe_run_location(path):
    run = Path(path).resolve()
    parent = (BACKEND / "model" / "candidates").resolve()
    if run == parent or not run.is_relative_to(parent):
        raise ValueError("Run directories must be below backend/model/candidates, never in the dataset")
    return run


CONTRACT = {"input_shape": [224, 224, 3], "dtype": "float32", "pixel_range": [0, 255],
            "decode": "Pillow RGB; no EXIF transpose", "resize": "TensorFlow bilinear antialias=False",
            "normalization": "EfficientNetB0 internal ImageNet preprocessing; NO external /255",
            "labels": {"Fake": 0, "Real": 1}, "output": "pReal", "decision": "REAL iff pReal >= threshold"}


def sha256(path):
    return rm.evaluation.sha256_file(Path(path))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_json(path, payload):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    os.replace(temporary, path)


def free_memory_gb():
    if platform.system() == "Windows":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(name, ctypes.c_ulonglong) for name in
                ("total_physical", "available_physical", "total_page", "available_page", "total_virtual", "available_virtual", "extended")]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError("Cannot query available physical RAM")
        return status.available_physical / 1024**3
    try:
        return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1024**3
    except (ValueError, AttributeError):
        return None


def memory_gate(minimum):
    available = free_memory_gb()
    if available is not None and available < minimum:
        raise RuntimeError(f"Only {available:.2f} GiB physical RAM is free; need {minimum:.2f} GiB. Close unused applications or use a training machine. No other process was stopped.")
    return available


def make_plan(rows):
    """Test membership unchanged; drop earlier-split copies, never relabel."""
    if any(not r["valid"] or r["split"] not in {"train", "validation", "test"} or r["label"] not in {0, 1} for r in rows):
        raise ValueError("Invalid images or unknown labels exist. Review inspection report before creating a training plan.")
    groups = defaultdict(list)
    for row in rows:
        groups[row["pixel_sha256"]].append(row)
    retained, excluded = [], []
    for group in groups.values():
        if len({r["label"] for r in group}) > 1:
            raise ValueError(f"Contradictory labels for identical pixels: {[r['path'] for r in group[:8]]}. Resolve label provenance; no label is guessed.")
        priority = {"test": 0, "validation": 1, "train": 2}
        ordered = sorted(group, key=lambda r: (priority[r["split"]], r["path"]))
        winner = ordered[0]
        for row in ordered:
            if row is winner or row["split"] == "test":
                retained.append(row)
            else:
                excluded.append({"path": row["path"], "split": row["split"], "label": row["label"],
                                 "reason": "Identical decoded RGB pixels; held-out split takes priority, then lexicographic first within split",
                                 "retained_reference": winner["path"]})
    retained.sort(key=lambda r: (r["split"], r["path"]))
    counts = Counter(f"{r['split']}/{r['label_name']}" for r in retained)
    if any(counts[f"{s}/{c}"] == 0 for s in ("train", "validation", "test") for c in ("Fake", "Real")):
        raise ValueError("Both classes must remain in every split after duplicate exclusion")
    return retained, excluded, dict(counts)


def prepare(args):
    global CURRENT_RUN
    inspection = args.inspection.resolve(strict=True)
    report = read_json(inspection / "inspection.json")
    root = Path(report["dataset_root"]).resolve(strict=True)
    run = safe_run_location(args.run_dir)
    if run.exists() or run.is_relative_to(root):
        raise ValueError("Run directory must be new and outside the original dataset")
    if report["layout_errors"] or report["unlabelled_files"] or report["invalid_file_count"]:
        raise ValueError("Dataset has unresolved integrity or label problems; review inspection.json and invalid_files.json")
    with (inspection / "inventory.jsonl").open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    retained, excluded, counts = make_plan(rows)
    run.mkdir(parents=True, exist_ok=False)
    CURRENT_RUN = run
    backup = BACKEND / "model" / "backups" / run.name
    backup.mkdir(parents=True, exist_ok=False)
    artifacts = {}
    for path in (ORIGINAL_MODEL, ORIGINAL_THRESHOLD):
        original_hash = sha256(path)
        shutil.copy2(path, backup / path.name)
        if sha256(backup / path.name) != original_hash:
            raise RuntimeError("Backup verification failed")
        artifacts[path.name] = {"source": str(path), "backup": str(backup / path.name), "sha256": original_hash}
    rm.save_json(backup / "backup_manifest.json", artifacts)
    with (run / "manifest.jsonl").open("x", encoding="utf-8") as f:
        for row in retained:
            f.write(json.dumps(row) + "\n")
    rm.save_json(run / "excluded_duplicates.json", excluded)
    config = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
              "dataset_root": str(root), "inspection": str(inspection), "inspection_sha256": sha256(inspection / "inspection.json"),
              "inventory_sha256": sha256(inspection / "inventory.jsonl"), "manifest_sha256": sha256(run / "manifest.jsonl"),
              "original_artifacts": artifacts, "counts": counts, "excluded_duplicate_copies": len(excluded),
              "contract": CONTRACT, "software": rm.evaluation.package_versions(),
              "source_sha256": {p.name: sha256(p) for p in [Path(__file__), Path(__file__).with_name("retraining_metrics.py"),
                  Path(__file__).with_name("evaluation_plots.py"), BACKEND / "app" / "services" / "preprocessing.py"]},
              "seed": args.seed, "batch_size": args.batch_size, "threads": args.threads,
              "head_epochs": args.head_epochs, "fine_epochs": args.fine_epochs, "head_lr": .001, "fine_lr": .00001,
              "minimum_free_ram_gb": args.minimum_free_ram_gb, "minimum_class_recall": .80,
              "promotion_policy": {"accuracy": "strictly greater than existing on fixed test", "balanced_accuracy": "strictly greater",
                  "per_class_recall": ">=0.80 each and neither worse than existing", "validation_recall_constraint": "must pass",
                  "paired_correctness_test": "one-sided exact paired binomial p<0.05 (exploratory; image-independence limitation)"},
              "pretrained_weights": "ImageNet; do not initialize from original trained classifier",
              "augmentation": "seeded horizontal flip and rotation +/-0.02 turns; no color/JPEG/crop corruption",
              "fine_tuning": "only block6*, block7*, top_conv; all BatchNormalization frozen; backbone call training=False",
              "pipeline": "shuffle paths, decode one batch lazily, no in-memory image cache, prefetch 1, private threadpool 1",
              "deduplication": "Test stays unchanged. Identical-pixel copies excluded from train before validation/test, and validation before test. First path retained within train/validation.",
              "limitations": ["Existing model's training provenance is unavailable; independence of its original test exposure is not verifiable.",
                             "Hash separation cannot ensure distinct identities, source videos, or generation methods.",
                             "Folder labels are supplied ground truth, not independently verified authenticity.",
                             "Backups every 500 batches preserve current and previous checkpoints; restart repeats the interrupted epoch from saved weights, and need not be bitwise identical."]}
    rm.save_json(run / "config.json", config)
    print(json.dumps({"run": str(run), "backup": str(backup), "counts": counts, "excluded_duplicates": len(excluded)}, indent=2), flush=True)


def load_run(run):
    global CURRENT_RUN
    run = safe_run_location(run).resolve(strict=True)
    config = read_json(run / "config.json")
    if run.is_relative_to(Path(config["dataset_root"]).resolve()):
        raise ValueError("Run directory cannot be inside the source dataset")
    if sha256(run / "manifest.jsonl") != config["manifest_sha256"]:
        raise ValueError("Frozen data manifest changed")
    for artifact in config["original_artifacts"].values():
        if sha256(artifact["backup"]) != artifact["sha256"]:
            raise ValueError("Original-model backup changed")
    with (run / "manifest.jsonl").open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    CURRENT_RUN = run
    return run, config, rows


def setup_tf(config):
    memory_gate(config["minimum_free_ram_gb"])
    import tensorflow as tf
    tf.config.threading.set_intra_op_parallelism_threads(config["threads"])
    tf.config.threading.set_inter_op_parallelism_threads(1)
    tf.keras.utils.set_random_seed(config["seed"])
    tf.config.experimental.enable_op_determinism()
    for gpu in tf.config.list_physical_devices("GPU"):
        tf.config.experimental.set_memory_growth(gpu, True)
    return tf


def dataset(tf, rows, config, training=False):
    import numpy as np
    from PIL import Image
    from io import BytesIO
    root = Path(config["dataset_root"])
    paths = [str(root / row["path"]) for row in rows]
    hashes = [row["sha256"] for row in rows]
    labels = [row["label"] for row in rows]
    def decode(path, expected_hash):
        filename = path.numpy().decode("utf-8")
        data = Path(filename).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected_hash.numpy().decode("utf-8"):
            raise ValueError(f"Dataset file changed since inspection: {filename}")
        with Image.open(BytesIO(data)) as image:
            return np.asarray(image.convert("RGB"), dtype=np.float32)
    def transform(path, digest, label):
        image = tf.py_function(decode, [path, digest], tf.float32)
        image.set_shape([None, None, 3])
        image = tf.image.resize(image, [224, 224], method="bilinear", antialias=False)
        return image, tf.cast(tf.reshape(label, [1]), tf.float32)
    ds = tf.data.Dataset.from_tensor_slices((paths, hashes, labels))
    if training:
        ds = ds.shuffle(len(rows), seed=config["seed"], reshuffle_each_iteration=True)
    ds = ds.map(transform, num_parallel_calls=1, deterministic=True).batch(config["batch_size"]).prefetch(1)
    options = tf.data.Options()
    options.experimental_deterministic = True
    options.threading.private_threadpool_size = 1
    options.threading.max_intra_op_parallelism = 1
    return ds.with_options(options)


def score(tf, model, rows, config, name):
    import numpy as np
    values = []
    start = time.monotonic()
    for index, (images, _) in enumerate(dataset(tf, rows, config)):
        output = np.asarray(model(images, training=False))
        if output.shape != (len(images), 1) or not np.isfinite(output).all() or output.min() < 0 or output.max() > 1:
            raise ValueError("Invalid model probability output")
        values.extend(float(p) for p in output[:, 0])
        if index % 250 == 0:
            print(f"{name}: {len(values):,}/{len(rows):,} images ({time.monotonic()-start:.1f}s)", flush=True)
    return values


def audit(args):
    run, config, rows = load_run(args.run_dir)
    if (run / "existing_validation_complete.json").exists():
        raise ValueError("Existing-model audit already completed; inspect saved results")
    tf = setup_tf(config)
    original = config["original_artifacts"]["deepfake_model.keras"]["backup"]
    model = tf.keras.models.load_model(original, compile=False, safe_mode=True)
    model.summary(print_fn=lambda text: print(text, flush=True))
    (run / "existing_model_architecture.json").write_text(model.to_json(), encoding="utf-8")
    backbone = model.get_layer("efficientnetb0")
    report = {"input_shape": model.input_shape, "output_shape": model.output_shape, "parameters": model.count_params(),
              "backbone_trainable": backbone.trainable, "trainable_parameters": int(sum(rm.np.prod(w.shape) for w in model.trainable_weights)),
              "internal_preprocessing": [{"name": layer.name, "class": layer.__class__.__name__, "config": layer.get_config()}
                                         for layer in backbone.layers if layer.__class__.__name__ in ("Rescaling", "Normalization")],
              "normalization_weights": [v.tolist() for v in backbone.get_layer("normalization").get_weights()],
              "label_mapping_status": "Backend and requested mapping Fake=0/Real=1 agree; original training class_indices not available",
              "overfitting_status": "Cannot establish overfitting without original training history and split provenance",
              "environment": {"python": sys.version, "tensorflow": tf.__version__, "keras": tf.keras.__version__,
                              "gpus": [str(g) for g in tf.config.list_physical_devices("GPU")], "build": tf.sysconfig.get_build_info()}}
    atomic_json(run / "existing_model_audit.json", report)
    train_rows = [r for r in rows if r["split"] == "train"]
    mini = train_rows[:config["batch_size"] * 8]
    timing_start = time.monotonic()
    score(tf, model, mini, config, "CPU/GPU benchmark (training images only, not accuracy)")
    elapsed = time.monotonic() - timing_start
    atomic_json(run / "benchmark.json", {"images": len(mini), "elapsed_seconds": elapsed,
        "images_per_second_with_warmup": len(mini)/elapsed,
        "estimated_forward_only_train_epoch_seconds": elapsed/len(mini)*len(train_rows),
        "warning": "Short warmup-inclusive inference timing, not a measured training epoch; fine-tuning is slower"})
    validation = [r for r in rows if r["split"] == "validation"]
    cache = run / "existing_validation_scores.json"
    if cache.exists():
        probabilities = read_json(cache)
    else:
        probabilities = score(tf, model, validation, config, "existing validation")
        rm.save_json(cache, probabilities)
    threshold = read_json(config["original_artifacts"]["threshold.json"]["backup"])["threshold"]
    result = rm.save_evaluation(run, "existing_validation", validation, probabilities, threshold)
    print(json.dumps(result, indent=2), flush=True)


def compile_model(tf, model, lr):
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=lr), loss="binary_crossentropy",
                  metrics=[tf.keras.metrics.BinaryAccuracy(name="accuracy"), tf.keras.metrics.AUC(name="auc_real"),
                           tf.keras.metrics.Recall(name="recall_real"), tf.keras.metrics.TrueNegatives(name="correct_fake"),
                           tf.keras.metrics.FalsePositives(name="fake_as_real")])


def new_model(tf, config):
    backbone = tf.keras.applications.EfficientNetB0(include_top=False, weights="imagenet", input_shape=(224,224,3))
    backbone.trainable = False
    inputs = tf.keras.Input((224,224,3), dtype="float32")
    x = tf.keras.layers.RandomFlip("horizontal", seed=config["seed"])(inputs)
    x = tf.keras.layers.RandomRotation(.02, fill_mode="reflect", seed=config["seed"]+1)(x)
    x = backbone(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(.3, seed=config["seed"]+2)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid", name="deepfake_prediction")(x)
    model = tf.keras.Model(inputs, outputs, name="deeptrace_efficientnetb0_v2")
    compile_model(tf, model, config["head_lr"])
    return model


def fine_tune(tf, model, config):
    backbone = model.get_layer("efficientnetb0")
    backbone.trainable = True
    for layer in backbone.layers:
        layer.trainable = layer.name.startswith(("block6", "block7", "top_conv")) and not isinstance(layer, tf.keras.layers.BatchNormalization)
    compile_model(tf, model, config["fine_lr"])


def publish_candidate(checkpoint, candidate):
    checkpoint, candidate = Path(checkpoint), Path(candidate)
    if candidate.exists():
        if sha256(candidate) != sha256(checkpoint):
            raise ValueError("Existing candidate differs from the validation-loss-selected checkpoint")
        return
    temporary = candidate.with_name(candidate.name + ".tmp")
    shutil.copy2(checkpoint, temporary)
    rm.publish_new(temporary, candidate)
    temporary.unlink()


def epoch_checkpoint_directory(run, stage):
    """Keep every completed epoch, including earlier copies of a resumed epoch."""
    if stage not in {"head", "fine"}:
        raise ValueError("Unknown training stage")
    parent = Path(run) / "epoch_checkpoints" / stage
    parent.mkdir(parents=True, exist_ok=True)
    attempt = 1
    while True:
        destination = parent / f"attempt-{attempt:03d}"
        try:
            destination.mkdir(exist_ok=False)
            return destination
        except FileExistsError:
            attempt += 1


def validated_history(rows, saved_epoch):
    if type(saved_epoch) is not int or saved_epoch < 0 or len(rows) != saved_epoch:
        raise ValueError("History must contain exactly the completed epochs")
    records = []
    for expected, row in enumerate(rows):
        if str(row.get("epoch")) != str(expected):
            raise ValueError("History epochs must be unique, ordered, and contiguous")
        loss = float(row["val_loss"])
        if not math.isfinite(loss) or loss < 0:
            raise ValueError("Invalid historical validation loss")
        records.append((expected, loss))
    return records


def new_controllers(tf, stage):
    if stage not in {"head", "fine"}:
        raise ValueError("Unknown training stage")
    return (tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=2 if stage == "head" else 3,
                restore_best_weights=False),
            tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=.5, patience=1, min_lr=1e-7))


def reconstruct_controllers(tf, config, stage, records):
    # Reconstruct against a separate optimizer: never reduce the restored LR twice.
    dummy = SimpleNamespace(stop_training=False,
                            optimizer=tf.keras.optimizers.Adam(learning_rate=config[stage + "_lr"]))
    early, reduce = new_controllers(tf, stage)
    for callback in (early, reduce):
        callback.set_model(dummy)
        callback.on_train_begin()
    for epoch, loss in records:
        if dummy.stop_training:
            raise ValueError("History extends beyond an already-stopped stage")
        for callback in (early, reduce):
            callback.on_epoch_end(epoch, {"val_loss": loss})
    if dummy.stop_training:
        raise ValueError("History indicates the stage already stopped; inspect completion state")
    return dummy, early, reduce


def controller_state(model, early, reduce):
    return {"learning_rate": float(model.optimizer.learning_rate.numpy()),
            "stop_training": bool(model.stop_training),
            "early": {"best": None if early.best is None else float(early.best), "wait": early.wait,
                      "best_epoch": early.best_epoch, "stopped_epoch": early.stopped_epoch,
                      "min_delta": early.min_delta},
            "reduce": {"best": None if reduce.best is None else float(reduce.best), "wait": reduce.wait,
                       "cooldown_counter": reduce.cooldown_counter, "min_delta": reduce.min_delta}}


def recovery_callbacks(tf, config, stage, rows, saved_epoch, expected_iteration, backup_dir):
    records = validated_history(rows, saved_epoch)
    if saved_epoch >= config[stage + "_epochs"] or type(expected_iteration) is not int or expected_iteration < 0:
        raise ValueError("Invalid recovery position")
    early, reduce = new_controllers(tf, stage)

    class EpochAwareBackupAndRestore(tf.keras.callbacks.BackupAndRestore):
        def on_train_begin(self, logs=None):
            # The execution record verifies the staged primary before fit. Fail
            # closed on restore errors; do not silently repair/overwrite it.
            self._load_model()

        def on_epoch_begin(self, epoch, logs=None):
            super().on_epoch_begin(epoch, logs)
            if type(epoch) is not int or epoch < 0:
                raise ValueError("Invalid actual epoch")
            self._current_epoch = epoch

    class RestoreControllerHistory(tf.keras.callbacks.Callback):
        def on_train_begin(self, logs=None):
            if self.model._initial_epoch != saved_epoch:
                raise ValueError("Loaded checkpoint epoch differs from verified recovery plan")
            if int(self.model.optimizer.iterations.numpy()) != expected_iteration:
                raise ValueError("Loaded optimizer iteration differs from verified recovery plan")
            dummy, historical_early, historical_reduce = reconstruct_controllers(tf, config, stage, records)
            if not math.isclose(float(self.model.optimizer.learning_rate.numpy()),
                                float(dummy.optimizer.learning_rate.numpy()), rel_tol=1e-6, abs_tol=1e-12):
                raise ValueError("Checkpoint learning rate and reconstructed history disagree")
            # Keep monitor_op and signed min_delta together to avoid a double flip.
            for attribute in ("best", "wait", "best_epoch", "stopped_epoch", "best_weights", "monitor_op", "min_delta"):
                setattr(early, attribute, getattr(historical_early, attribute))
            for attribute in ("best", "wait", "cooldown_counter", "monitor_op", "min_delta"):
                setattr(reduce, attribute, getattr(historical_reduce, attribute))
            if self.model.stop_training:
                raise ValueError("Unexpected stopped model at recovery initialization")
            self.restored_state = controller_state(self.model, early, reduce)
            print("RECOVERY_RESTORED " + json.dumps({"stage": stage, "epoch_index": saved_epoch,
                "optimizer_iteration": expected_iteration, "replay_batch_index": 0,
                "controllers": self.restored_state}), flush=True)

    backup = EpochAwareBackupAndRestore(backup_dir, save_freq=500, double_checkpoint=True, delete_checkpoint=False)
    return backup, early, reduce, RestoreControllerHistory()


def validate_training_execution(run, config, recovery_record=None):
    """Validate an explicit append-only revision; never replace the original lock.

    Checkpoint hashing occurs only during trainer startup/offline preflight, not
    in a live external watchdog. An advanced checkpoint needs a new approved record.
    """
    run = Path(run).resolve(strict=True)
    execution = {"config_sha256": sha256(run / "config.json"), "source_sha256": {
        name: sha256(BACKEND / "app" / "services" / name if name == "preprocessing.py" else Path(__file__).with_name(name))
        for name in config["source_sha256"]}}
    lock_path = run / "training_execution_lock.json"
    if recovery_record is None:
        if lock_path.exists() and read_json(lock_path) != execution:
            raise ValueError("Frozen execution differs; an explicit approved --recovery-record is required")
        rm.save_json(lock_path, execution)
        return None
    record_path = Path(recovery_record).resolve(strict=True)
    if record_path.parent != (run / "recovery-executions").resolve() or record_path.suffix != ".json":
        raise ValueError("Recovery record must be an explicit JSON file in this run's recovery-executions directory")
    record, original = read_json(record_path), read_json(lock_path)
    if record.get("schema_version") != 1 or record.get("run_name") != run.name:
        raise ValueError("Recovery record schema/run mismatch")
    if record.get("original_execution_lock_sha256") != sha256(lock_path) or record.get("original_execution") != original:
        raise ValueError("Original execution lock integrity mismatch")
    if record.get("execution") != execution or execution["config_sha256"] != original["config_sha256"]:
        raise ValueError("Approved recovery source/config integrity mismatch")
    if any(execution["source_sha256"].get(name) != value for name, value in original["source_sha256"].items() if name != "retrain.py"):
        raise ValueError("Recovery permits only the approved retrain.py source revision")
    names = {"original_source", "original_lock_copy", "zero_primary", "preservation_manifest", "dataset_audit",
             "isolated_tests", "fallback_snapshot_manifest", "snapshot_weights", "snapshot_metadata",
             "active_weights", "active_metadata", "history", "training_state"}
    evidence = record.get("evidence", {})
    if set(evidence) != names:
        raise ValueError("Recovery evidence set is incomplete or unexpected")
    paths = {}
    for name, item in evidence.items():
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Recovery evidence must use run-relative paths")
        path = (run / relative).resolve(strict=True)
        if not path.is_relative_to(run) or not path.is_file() or sha256(path) != item["sha256"]:
            raise ValueError(f"Recovery evidence integrity mismatch: {name}")
        paths[name] = path
    if evidence["original_source"]["sha256"] != original["source_sha256"]["retrain.py"]:
        raise ValueError("Preserved original source does not match the historical lock")
    if evidence["original_lock_copy"]["sha256"] != sha256(lock_path) or paths["zero_primary"].stat().st_size != 0:
        raise ValueError("Preserved lock/forensic evidence mismatch")
    r = record["recovery"]
    if r.get("stage") != "head" or r.get("mode") != "replay_epoch_from_start" or r.get("restart_batch_index") != 0:
        raise ValueError("Only the approved full head-epoch replay is permitted")
    if type(r.get("epoch_index")) is not int or not 0 <= r["epoch_index"] < config["head_epochs"]:
        raise ValueError("Invalid recovery epoch")
    if type(r.get("optimizer_iteration")) is not int or r["optimizer_iteration"] < 0:
        raise ValueError("Invalid recovery optimizer iteration")
    if paths["active_weights"] != run / "resume_head/latest.weights.h5" or paths["active_metadata"] != run / "resume_head/training_metadata.json":
        raise ValueError("Recovery must use this run's active head directory, never the snapshot")
    if paths["active_weights"].stat().st_size == 0:
        raise ValueError("Zero-byte primary cannot be used")
    snapshot_dir = paths["fallback_snapshot_manifest"].parent
    if not snapshot_dir.is_relative_to(run / "recovery-snapshots") or any(paths[n].parent != snapshot_dir for n in ("snapshot_weights", "snapshot_metadata")):
        raise ValueError("Fallback snapshot paths do not belong to the same preserved snapshot")
    if any(evidence["active_" + name]["sha256"] != evidence["snapshot_" + name]["sha256"] for name in ("weights", "metadata")):
        raise ValueError("Active recovery files differ from the approved fallback")
    expected_metadata = {"epoch": r["epoch_index"], "batch": r["saved_batch_index"]}
    if read_json(paths["active_metadata"]) != expected_metadata or read_json(paths["snapshot_metadata"]) != expected_metadata:
        raise ValueError("Recovery metadata mismatch")
    if paths["history"] != run / "history_head.csv" or paths["training_state"] != run / "training_state.json":
        raise ValueError("Recovery must bind the actual training history/state")
    state = read_json(paths["training_state"])
    if state.get("running_stage") != "head" or state.get("completed_stages") != []:
        raise ValueError("Training state has advanced or differs from the approved recovery")
    with paths["history"].open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    validated_history(rows, r["epoch_index"])
    audit = read_json(paths["dataset_audit"])
    if audit.get("status") != "PASS" or not audit.get("dataset_membership_unchanged") or audit.get("dataset_files_verified") != 190335:
        raise ValueError("Completed dataset audit evidence is invalid")
    if sha256(run / "manifest.jsonl") != config["manifest_sha256"] or audit["checks"]["manifest"]["sha256"] != config["manifest_sha256"]:
        raise ValueError("Frozen dataset manifest/audit mismatch")
    for artifact in config["original_artifacts"].values():
        if sha256(artifact["source"]) != artifact["sha256"] or sha256(artifact["backup"]) != artifact["sha256"]:
            raise ValueError("Production artifact or original backup changed")
    return {**r, "history_rows": rows, "runtime": record["runtime"],
            "record_path": str(record_path), "record_sha256": sha256(record_path),
            "original_execution_lock_sha256": sha256(lock_path)}


def require_recovery_runtime(tf, recovery):
    expected = recovery["runtime"]
    if platform.system() != "Linux" or tf.__version__ != expected["tensorflow"] or tf.keras.__version__ != expected["keras"]:
        raise RuntimeError("Recovery requires the approved Linux TensorFlow/Keras runtime")
    if sys.prefix != expected["python_environment"] or os.environ.get("HDF5_USE_FILE_LOCKING", "TRUE").upper() in {"FALSE", "OFF", "0"}:
        raise RuntimeError("Recovery environment or HDF5 locking policy mismatch")
    gpus = tf.config.list_physical_devices("GPU")
    if not any(expected["gpu_name_contains"] in tf.config.experimental.get_device_details(g).get("device_name", "") for g in gpus):
        raise RuntimeError("Approved RTX GPU unavailable; CPU recovery is forbidden")
    tf.config.set_soft_device_placement(False)
    with tf.device("/GPU:0"):
        product = tf.matmul(tf.constant([[1., 2.], [3., 4.]]), tf.eye(2))
    if "/device:GPU:0" not in product.device or product.numpy().tolist() != [[1., 2.], [3., 4.]]:
        raise RuntimeError("Recovery GPU calculation failed")


def training_callbacks(tf, run, config, stage, history_path, prior_best, recovery=None):
    class Progress(tf.keras.callbacks.Callback):
        def on_epoch_begin(self, epoch, logs=None):
            self.started = time.monotonic()
            self.epoch = epoch
            memory_gate(config["minimum_free_ram_gb"])

        def on_train_batch_begin(self, batch, logs=None):
            memory_gate(config["minimum_free_ram_gb"])

        def on_test_batch_begin(self, batch, logs=None):
            # Keras invokes this hook for validation within fit(), too.
            memory_gate(config["minimum_free_ram_gb"])

        def on_train_batch_end(self, batch, logs=None):
            if batch % 250 == 0:
                atomic_json(run / "progress.json", {"stage": stage, "epoch": self.epoch+1, "batch": batch+1,
                            "elapsed_epoch_seconds": time.monotonic()-self.started,
                            "metrics": {k: float(v) for k,v in (logs or {}).items()}})
                print(f"{stage} epoch {self.epoch+1} batch {batch+1}: {logs}", flush=True)

        def on_epoch_end(self, epoch, logs=None):
            atomic_json(run / "progress.json", {"stage": stage, "completed_epoch": epoch+1,
                        "metrics": {k: float(v) for k,v in (logs or {}).items()}})

    if recovery is not None:
        backup, early, reduce, restore_history = recovery_callbacks(tf, config, stage,
            recovery["history_rows"], recovery["epoch_index"], recovery["optimizer_iteration"], str(run / f"resume_{stage}"))
    else:
        backup = tf.keras.callbacks.BackupAndRestore(str(run / f"resume_{stage}"), save_freq=500,
                    double_checkpoint=True, delete_checkpoint=False)
        early, reduce = new_controllers(tf, stage)
        restore_history = None
    archive = epoch_checkpoint_directory(run, stage)
    callbacks = [backup,
            tf.keras.callbacks.ModelCheckpoint(str(run / f"best_{stage}.keras"), monitor="val_loss",
                save_best_only=True, initial_value_threshold=prior_best),
            tf.keras.callbacks.ModelCheckpoint(str(archive / "epoch-{epoch:03d}.keras"),
                save_freq="epoch", save_best_only=False, save_weights_only=False),
            tf.keras.callbacks.CSVLogger(str(history_path), append=history_path.exists()),
            early, reduce, tf.keras.callbacks.TerminateOnNaN()]
    if restore_history is not None:
        callbacks.append(restore_history)  # After the controllers reset on_train_begin.
    return callbacks + [Progress()]


def train(args):
    run, config, rows = load_run(args.run_dir)
    if (run / "final_test_lock.json").exists() or (run / "selection.json").exists():
        raise ValueError("Candidate already frozen or test consumed; no further training allowed in this run")
    if not (run / "existing_validation_complete.json").exists():
        raise ValueError("Complete existing-model validation audit before training")
    recovery = validate_training_execution(run, config, getattr(args, "recovery_record", None))
    tf = setup_tf(config)
    if recovery is not None:
        require_recovery_runtime(tf, recovery)
    training = [r for r in rows if r["split"] == "train"]
    validation = [r for r in rows if r["split"] == "validation"]
    train_data = dataset(tf, training, config, training=True)
    validation_data = dataset(tf, validation, config)
    class_counts = Counter(r["label"] for r in training)
    class_weights = {label: len(training)/(2*count) for label, count in class_counts.items()}
    state_path = run / "training_state.json"
    state = read_json(state_path) if state_path.exists() else {"completed_stages": [], "class_weights": class_weights}
    model = None
    for stage, epochs in (("head", config["head_epochs"]), ("fine", config["fine_epochs"])):
        if stage in state["completed_stages"]:
            continue
        if stage == "head":
            model = new_model(tf, config)
        else:
            model = tf.keras.models.load_model(run / "best_head.keras", compile=False, safe_mode=True)
            fine_tune(tf, model, config)
        history_path = run / f"history_{stage}.csv"
        prior_best = float("inf")
        if history_path.exists():
            with history_path.open(newline="", encoding="utf-8") as f:
                prior_best = min((float(r["val_loss"]) for r in csv.DictReader(f)), default=float("inf"))
        callbacks = training_callbacks(tf, run, config, stage, history_path, prior_best,
            recovery=recovery if recovery is not None and recovery["stage"] == stage else None)
        atomic_json(state_path, {**state, "running_stage": stage})
        model.fit(train_data, validation_data=validation_data, epochs=epochs, callbacks=callbacks,
                  class_weight=class_weights, verbose=2)
        if not (run / f"best_{stage}.keras").exists():
            raise RuntimeError(f"Stage {stage} produced no finite checkpoint")
        state["completed_stages"].append(stage)
        atomic_json(state_path, state)
        del callbacks
        del model
        tf.keras.backend.clear_session()
    bests = {}
    for stage in ("head", "fine"):
        with (run / f"history_{stage}.csv").open(newline="", encoding="utf-8") as f:
            bests[stage] = min(float(r["val_loss"]) for r in csv.DictReader(f))
    chosen = min(bests, key=bests.get)
    candidate = run / "deepfake_model_v2.keras"
    selected_checkpoint = run / f"best_{chosen}.keras"
    publish_candidate(selected_checkpoint, candidate)
    cache = run / "candidate_validation_scores.json"
    if cache.exists():
        probabilities = read_json(cache)
    else:
        model = tf.keras.models.load_model(candidate, compile=False, safe_mode=True)
        probabilities = score(tf, model, validation, config, "candidate validation")
        rm.save_json(cache, probabilities)
    selection, threshold_rows = rm.choose_threshold([r["label"] for r in validation], probabilities,
        split="validation", minimum_recall=config["minimum_class_recall"])
    rm.save_csv(run / "validation_thresholds.csv", threshold_rows)
    rm.save_evaluation(run, "candidate_validation", validation, probabilities, selection["threshold"])
    threshold_path = run / "threshold.json"
    rm.save_json(threshold_path, {"threshold": selection["threshold"], "model_sha256": sha256(candidate), "contract": CONTRACT,
                 "selection_split": "validation", "criterion": selection["criterion"]})
    selection.update(candidate=str(candidate), candidate_sha256=sha256(candidate), threshold_sha256=sha256(threshold_path),
                     selected_stage=chosen, best_validation_losses=bests, config_sha256=sha256(run / "config.json"),
                     frozen_utc=datetime.now(timezone.utc).isoformat())
    if recovery is not None:
        selection["recovery_execution"] = {key: recovery[key] for key in
            ("record_path", "record_sha256", "original_execution_lock_sha256")}
    rm.save_json(run / "selection.json", selection)
    print(json.dumps(selection, indent=2), flush=True)


def finalize(args):
    run, config, rows = load_run(args.run_dir)
    selection = read_json(run / "selection.json")
    if (run / "comparison.json").exists():
        raise ValueError("Final test already completed; no repeated test evaluation")
    if sha256(selection["candidate"]) != selection["candidate_sha256"] or sha256(run / "threshold.json") != selection["threshold_sha256"] or sha256(run / "config.json") != selection["config_sha256"]:
        raise ValueError("Frozen candidate, threshold or configuration changed")
    locked = {"candidate_sha256": selection["candidate_sha256"], "threshold_sha256": selection["threshold_sha256"],
              "config_sha256": selection["config_sha256"], "manifest_sha256": config["manifest_sha256"],
              "selection_sha256": sha256(run / "selection.json"), "existing": config["original_artifacts"]}
    lock_path = run / "final_test_lock.json"
    if lock_path.exists():
        if read_json(lock_path)["artifacts"] != locked:
            raise ValueError("Final-test lock mismatch; cannot tune after test access")
    else:
        memory_gate(config["minimum_free_ram_gb"])
        rm.save_json(lock_path, {"artifacts": locked, "started_utc": datetime.now(timezone.utc).isoformat()})
    tf = setup_tf(config)
    test_rows = [r for r in rows if r["split"] == "test"]
    results, scores = {}, {}
    for name, model_path, threshold in (("existing", config["original_artifacts"]["deepfake_model.keras"]["backup"],
            read_json(config["original_artifacts"]["threshold.json"]["backup"])["threshold"]),
            ("candidate", selection["candidate"], selection["threshold"])):
        cache = run / f"{name}_test_scores.json"
        if cache.exists():
            probabilities = read_json(cache)
        else:
            model = tf.keras.models.load_model(model_path, compile=False, safe_mode=True)
            probabilities = score(tf, model, test_rows, config, name + " final test")
            rm.save_json(cache, probabilities)
            del model
            tf.keras.backend.clear_session()
        results[name] = rm.save_evaluation(run, name + "_test", test_rows, probabilities, threshold)
        scores[name] = probabilities
    import numpy as np
    from scipy.stats import binomtest
    truth = np.asarray([r["label"] for r in test_rows])
    previous_t = results["existing"]["threshold_real"]
    old_correct = (np.asarray(scores["existing"]) >= previous_t) == truth
    new_correct = (np.asarray(scores["candidate"]) >= selection["threshold"]) == truth
    wins = int((new_correct & ~old_correct).sum())
    losses = int((old_correct & ~new_correct).sum())
    pvalue = float(binomtest(wins, wins+losses, .5, alternative="greater").pvalue) if wins+losses else 1.0
    old, new = results["existing"], results["candidate"]
    gates = {"accuracy_improved": new["accuracy"] > old["accuracy"],
             "balanced_accuracy_improved": new["balanced_accuracy"] > old["balanced_accuracy"],
             "real_recall_acceptable": new["recall_real"] >= max(config["minimum_class_recall"], old["recall_real"]),
             "fake_recall_acceptable": new["recall_fake"] >= max(config["minimum_class_recall"], old["recall_fake"]),
             "validation_recall_constraint": selection["recall_constraint_satisfied"], "paired_test_p_below_0_05": pvalue < .05,
             "no_duplicate_test_pixels": len({r["pixel_sha256"] for r in test_rows}) == len(test_rows)}
    comparison = {"existing": old, "candidate": new, "gates": gates, "eligible_for_promotion": all(gates.values()),
                  "paired_comparison": {"candidate_only_correct": wins, "existing_only_correct": losses, "one_sided_exact_p": pvalue},
                  "warning": "Exploratory paired test assumes independent images. Unverified original training/test provenance and related identities limit generalization claims.",
                  "test_membership": "All original Test files retained; no test threshold/model tuning", "active_model_changed": False}
    rm.save_json(run / "comparison.json", comparison)
    print(json.dumps(comparison, indent=2), flush=True)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="Freeze disjoint manifests/config and back up original artifacts")
    prep.add_argument("--inspection", type=Path, required=True)
    prep.add_argument("--seed", type=int, default=42)
    prep.add_argument("--batch-size", type=int, default=4)
    prep.add_argument("--threads", type=int, default=4)
    prep.add_argument("--head-epochs", type=int, default=5)
    prep.add_argument("--fine-epochs", type=int, default=8)
    prep.add_argument("--minimum-free-ram-gb", type=float, default=2.0)
    commands = [prep]
    for command, description in (("audit", "Load saved model, benchmark training images, evaluate validation ONLY"),
                                  ("train", "Train both stages and freeze validation-selected threshold; resumes epoch backup"),
                                  ("finalize", "Evaluate both fixed models on Test once; never tune")):
        command_parser = sub.add_parser(command, help=description)
        if command == "train":
            command_parser.add_argument("--recovery-record", type=Path,
                help="Explicit append-only recovery execution record; original lock remains immutable")
        commands.append(command_parser)
    for command in commands:
        command.add_argument("--run-dir", type=Path, required=True)
    return p


def main():
    global CURRENT_RUN
    CURRENT_RUN = None
    sys.dont_write_bytecode = True
    args = parser().parse_args()
    if args.command == "prepare" and (args.batch_size < 1 or args.threads < 1 or args.head_epochs < 1 or args.fine_epochs < 1 or not 0 <= args.seed < 2**31 or args.minimum_free_ram_gb < .5):
        raise ValueError("Invalid positive batch/thread/epoch count, seed, or minimum RAM")
    try:
        globals()[args.command](args)
    except (Exception, KeyboardInterrupt) as exc:
        if CURRENT_RUN is not None:
            atomic_json(CURRENT_RUN / "last_error.json", {"command": args.command, "error": str(exc),
                "type": type(exc).__name__, "utc": datetime.now(timezone.utc).isoformat(),
                "resume": "Run the same command. Training preserves completed-epoch backups; final evaluation locks fixed artifacts. Inspect partial selection outputs before resuming selection."})
        print(f"{args.command} stopped: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
