"""Mechanics-only fixtures: no synthetic image is evidence of detector accuracy."""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def load(name):
    spec = importlib.util.spec_from_file_location("test_owned_" + name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


inventory = load("inspect_dataset")
training = load("retrain")
rm = training.rm


def row(path, split, label, digest):
    return {"path": path, "split": split, "label": label, "label_name": "Real" if label else "Fake",
            "valid": True, "pixel_sha256": digest, "sha256": digest}


def complete_rows():
    return [row(f"{split}/{label}.png", split, label, f"{split}-{label}")
            for split in ("train", "validation", "test") for label in (0, 1)]


def test_hash_inventory_reports_corruption_duplicates_and_keeps_inputs(tmp_path):
    root = tmp_path / "data"
    for split in ("Train", "Validation", "Test"):
        for label in ("Fake", "Real"):
            path = root / split / label / "image.png"
            path.parent.mkdir(parents=True)
            Image.new("RGB", (8, 8), "red" if label == "Fake" else "green").save(path)
    broken = root / "Train" / "Real" / "broken.jpg"
    broken.write_bytes(b"invalid fixture")
    before = {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    report = inventory.inspect(root, tmp_path / "report", workers=1)
    assert report["total_files"] == 7
    assert report["valid_images"] == 6
    assert report["invalid_file_count"] == 1
    assert report["duplicate_summary"]["file_sha256"]["cross_split_groups"] == 2
    assert report["duplicate_summary"]["decoded_rgb_sha256"]["conflicting_label_groups"] == 0
    assert report["counts"]["train"]["Real"]["invalid_files"] == 1
    assert before == {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_inventory_output_cannot_be_inside_dataset(tmp_path):
    with pytest.raises(ValueError, match="outside"):
        inventory.inspect(tmp_path, tmp_path / "report")


def test_unknown_label_not_guessed_from_filename(tmp_path):
    path = tmp_path / "Train" / "unknown" / "real.jpg"
    path.parent.mkdir(parents=True)
    Image.new("RGB", (2, 2)).save(path)
    items, _, _ = inventory.discover(tmp_path)
    assert items[0][2] == "train"
    assert items[0][3] is None


def test_disjoint_plan_preserves_every_test_path():
    rows = complete_rows()
    rows.extend([row("train/copied_test.png", "train", 0, "test-0"),
                 row("validation/copied_test.png", "validation", 0, "test-0"),
                 row("test/duplicate.png", "test", 0, "test-0"),
                 row("train/copied_val.png", "train", 1, "validation-1")])
    retained, excluded, counts = training.make_plan(rows)
    assert {r["path"] for r in retained if r["split"] == "test"} == {r["path"] for r in rows if r["split"] == "test"}
    assert len(excluded) == 3
    by_split = {s: {r["pixel_sha256"] for r in retained if r["split"] == s} for s in ("train", "validation", "test")}
    assert not by_split["train"] & by_split["validation"]
    assert not by_split["train"] & by_split["test"]
    assert not by_split["validation"] & by_split["test"]
    assert counts["test/Fake"] == 2


def test_label_conflicts_block_training():
    rows = complete_rows() + [row("train/conflict.png", "train", 1, "test-0")]
    with pytest.raises(ValueError, match="Contradictory"):
        training.make_plan(rows)


def test_corruption_blocks_training():
    rows = complete_rows()
    rows[0]["valid"] = False
    with pytest.raises(ValueError, match="Invalid"):
        training.make_plan(rows)


def test_metrics_use_fake_positive_and_equal_threshold_is_real():
    result = rm.metrics([0, 0, 1, 1], [.2, .8, .3, .42], .42)
    assert result["confusion_matrix"]["rows_actual_columns_predicted"] == [[1, 1], [1, 1]]
    assert result["sensitivity"] == result["specificity"] == .5
    assert result["false_positive_rate"] == .5


@pytest.mark.parametrize("split", ["test", "train", "known"])
def test_threshold_selection_refuses_nonvalidation(split):
    with pytest.raises(ValueError, match="validation ONLY"):
        rm.choose_threshold([0, 1], [.1, .9], split=split)


def test_threshold_sweep_matches_bruteforce():
    rng = np.random.default_rng(42)
    labels = np.r_[np.zeros(100, dtype=int), np.ones(100, dtype=int)]
    scores = np.r_[rng.uniform(0, .5, 100), rng.uniform(.4, 1, 100)]
    selection, sweep = rm.choose_threshold(labels, scores, split="validation")
    for row_ in sweep:
        result = rm.metrics(labels, scores, row_["threshold"])
        assert row_["balanced_accuracy"] == pytest.approx(result["balanced_accuracy"])
        assert row_["recall_real"] == pytest.approx(result["recall_real"])
    feasible = [r for r in sweep if r["feasible"]]
    expected = max(feasible, key=lambda r: (r["balanced_accuracy"], r["recall_real"], -abs(r["threshold"]-.5)))
    assert selection["threshold"] == expected["threshold"]
    assert selection["recall_constraint_satisfied"]


def test_unlearned_scores_cannot_meet_promotion_constraint():
    selection, _ = rm.choose_threshold([0, 0, 1, 1], [.4, .4, .4, .4], split="validation")
    assert not selection["recall_constraint_satisfied"]
    assert selection["metrics"]["balanced_accuracy"] == .5


def test_available_memory_guard_does_not_import_tensorflow(monkeypatch):
    monkeypatch.setattr(training, "free_memory_gb", lambda: .4)
    with pytest.raises(RuntimeError, match="No other process"):
        training.memory_gate(2)


def test_saved_curves_predictions_and_confusion_matrix(tmp_path):
    rows = complete_rows()[:4]
    result = rm.save_evaluation(tmp_path, "fixture", rows, [.1, .9, .2, .8], .5)
    assert result["accuracy"] == 1
    assert json.loads((tmp_path / "fixture_metrics.json").read_text())["positive_class"] == "Fake"
    assert (tmp_path / "fixture_roc.csv").exists()
    assert (tmp_path / "fixture_precision_recall.csv").exists()
    assert (tmp_path / "fixture_confusion_matrix.csv").exists()
    assert (tmp_path / "fixture_complete.json").exists()


def test_rejected_run_location_does_not_write_to_dataset(tmp_path, monkeypatch):
    root = tmp_path / "dataset"
    root.mkdir()
    protected = root / "last_error.json"
    protected.write_text("do not replace")
    inspection = tmp_path / "inspection"
    inspection.mkdir()
    (inspection / "inspection.json").write_text(json.dumps({"dataset_root": str(root)}))
    monkeypatch.setattr(sys, "argv", ["retrain.py", "prepare", "--inspection", str(inspection), "--run-dir", str(root)])
    assert training.main() == 2
    assert protected.read_text() == "do not replace"
    assert len(list(root.iterdir())) == 1


def test_directory_traversal_errors_are_reported(tmp_path, monkeypatch):
    def failing_walk(root, *, followlinks, onerror):
        onerror(PermissionError(13, "Access denied", str(tmp_path / "Test")))
        return iter([])
    monkeypatch.setattr(inventory.os, "walk", failing_walk)
    _, _, errors = inventory.discover(tmp_path)
    assert len(errors) == 1
    assert "Unreadable directory" in errors[0]


def test_failed_json_write_never_exposes_partial_final_file(tmp_path):
    path = tmp_path / "lock.json"
    with pytest.raises(TypeError):
        rm.save_json(path, {"valid": 1, "bad": object()})
    assert not path.exists()
    rm.save_json(path, {"valid": 1})
    rm.save_json(path, {"valid": 1})  # Identical retry is safe.
    with pytest.raises(ValueError, match="different existing"):
        rm.save_json(path, {"valid": 2})
    assert json.loads(path.read_text()) == {"valid": 1}


def test_evaluation_repairs_an_interrupted_bundle_commit(tmp_path, monkeypatch):
    original_publish = rm.publish_new
    def fail_second_output(source, destination):
        if Path(destination).parent == tmp_path and len(list(tmp_path.glob("fixture_*"))) == 1:
            raise OSError("simulated interrupted bundle commit")
        return original_publish(source, destination)
    monkeypatch.setattr(rm, "publish_new", fail_second_output)
    rows = complete_rows()[:4]
    with pytest.raises(OSError, match="interrupted"):
        rm.save_evaluation(tmp_path, "fixture", rows, [.1, .9, .2, .8], .5)
    assert not (tmp_path / "fixture_complete.json").exists()
    monkeypatch.setattr(rm, "publish_new", original_publish)
    result = rm.save_evaluation(tmp_path, "fixture", rows, [.1, .9, .2, .8], .5)
    assert result["accuracy"] == 1
    marker = json.loads((tmp_path / "fixture_complete.json").read_text())
    assert len(marker["artifacts"]) == 8
    assert all((tmp_path / name).exists() for name in marker["artifacts"])
    with pytest.raises(ValueError, match="different inputs"):
        rm.save_evaluation(tmp_path, "fixture", rows, [.1, .9, .2, .8], .95)


def test_candidate_copy_is_resumable_but_never_replaced(tmp_path):
    checkpoint, candidate = tmp_path / "checkpoint.keras", tmp_path / "candidate.keras"
    checkpoint.write_bytes(b"checkpoint fixture, not a model")
    training.publish_candidate(checkpoint, candidate)
    training.publish_candidate(checkpoint, candidate)
    checkpoint.write_bytes(b"different checkpoint")
    with pytest.raises(ValueError, match="differs"):
        training.publish_candidate(checkpoint, candidate)
    assert candidate.read_bytes() == b"checkpoint fixture, not a model"


def fake_callback_api():
    """Exercise callback wiring without loading TensorFlow alongside an audit."""
    from types import SimpleNamespace

    def constructor(kind):
        return lambda *args, **kwargs: SimpleNamespace(kind=kind, args=args, kwargs=kwargs)

    callbacks = SimpleNamespace(Callback=object, **{
        name: constructor(name) for name in (
            "BackupAndRestore", "ModelCheckpoint", "CSVLogger", "EarlyStopping",
            "ReduceLROnPlateau", "TerminateOnNaN")})
    return SimpleNamespace(keras=SimpleNamespace(callbacks=callbacks))


@pytest.mark.parametrize("stage", ["head", "fine"])
def test_epoch_archives_keep_earlier_resumed_attempts(tmp_path, stage):
    first = training.epoch_checkpoint_directory(tmp_path, stage)
    saved = first / "epoch-001.keras"
    saved.write_bytes(b"completed epoch fixture")
    second = training.epoch_checkpoint_directory(tmp_path, stage)
    assert first.name == "attempt-001"
    assert second.name == "attempt-002"
    assert saved.read_bytes() == b"completed epoch fixture"
    assert second.parent == first.parent


def test_training_retains_every_epoch_without_changing_best_selection(tmp_path):
    callbacks = training.training_callbacks(fake_callback_api(), tmp_path,
        {"minimum_free_ram_gb": 2.0}, "head", tmp_path / "history_head.csv", .123)
    recovery, best, archive = callbacks[:3]
    assert recovery.kwargs == {"save_freq": 500, "double_checkpoint": True, "delete_checkpoint": False}
    assert best.kwargs == {"monitor": "val_loss", "save_best_only": True, "initial_value_threshold": .123}
    assert archive.kwargs == {"save_freq": "epoch", "save_best_only": False, "save_weights_only": False}
    assert Path(archive.args[0]).parent == tmp_path / "epoch_checkpoints" / "head" / "attempt-001"
    assert Path(archive.args[0]).name == "epoch-{epoch:03d}.keras"


@pytest.mark.parametrize("hook", ["on_epoch_begin", "on_train_batch_begin", "on_test_batch_begin"])
def test_training_and_validation_keep_configured_memory_floor(tmp_path, monkeypatch, hook):
    callbacks = training.training_callbacks(fake_callback_api(), tmp_path,
        {"minimum_free_ram_gb": 2.0}, "head", tmp_path / "history_head.csv", float("inf"))
    progress = callbacks[-1]
    monkeypatch.setattr(training, "free_memory_gb", lambda: 1.99)
    with pytest.raises(RuntimeError, match="need 2.00 GiB"):
        getattr(progress, hook)(0)
    monkeypatch.setattr(training, "free_memory_gb", lambda: 2.1)
    getattr(progress, hook)(0)


def test_training_progress_still_records_metrics(tmp_path, monkeypatch):
    monkeypatch.setattr(training, "free_memory_gb", lambda: 3.0)
    progress = training.training_callbacks(fake_callback_api(), tmp_path,
        {"minimum_free_ram_gb": 2.0}, "fine", tmp_path / "history_fine.csv", float("inf"))[-1]
    progress.on_epoch_begin(2)
    progress.on_train_batch_end(0, {"loss": .5})
    batch = json.loads((tmp_path / "progress.json").read_text())
    assert (batch["stage"], batch["epoch"], batch["batch"]) == ("fine", 3, 1)
    progress.on_epoch_end(2, {"loss": .4, "val_loss": .45})
    epoch = json.loads((tmp_path / "progress.json").read_text())
    assert epoch["completed_epoch"] == 3
    assert epoch["metrics"] == {"loss": .4, "val_loss": .45}
