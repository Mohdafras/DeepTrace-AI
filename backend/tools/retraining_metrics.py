"""Binary metrics and validation-only threshold selection (positive class = FAKE).

The sigmoid always means pReal; REAL iff pReal >= threshold. No training or
filesystem side effects on import. Curves are also saved as inspectable CSV.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_curve


def load_local(name):
    path = Path(__file__).resolve().with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("deeptrace_" + name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


evaluation = load_local("evaluate")


def metrics(labels, probabilities, threshold):
    result = evaluation.metrics([int(v) for v in labels], [float(v) for v in probabilities], float(threshold))
    result.update(precision=result["precision_fake"], recall=result["recall_fake"],
                  sensitivity=result["recall_fake"], specificity=result["recall_real"],
                  f1=result["f1_fake"], false_positive_rate=result["false_positive_rate_real_as_fake"],
                  false_negative_rate=result["false_negative_rate_fake_as_real"])
    result["macro_f1"] = (result["f1_fake"] + result["f1_real"]) / 2
    result["average_precision_fake"] = float(average_precision_score(1 - np.asarray(labels), 1 - np.asarray(probabilities)))
    return result


def choose_threshold(labels, probabilities, *, split, minimum_recall=0.80):
    if split != "validation":
        raise ValueError("Threshold selection is permitted on validation ONLY")
    # Reuse existing input validation before the vectorized sweep.
    metrics(labels, probabilities, 0.5)
    y, p = np.asarray(labels, dtype=int), np.asarray(probabilities, dtype=float)
    if len(np.unique(y)) != 2:
        raise ValueError("Both validation classes are required")
    if not 0 < minimum_recall <= 1:
        raise ValueError("Minimum per-class recall must be in (0,1]")
    thresholds = np.unique(np.r_[0.0, 0.5, 1.0, p])
    fake = np.sort(p[y == 0])
    real = np.sort(p[y == 1])
    recall_fake = np.searchsorted(fake, thresholds, side="left") / len(fake)
    recall_real = 1 - np.searchsorted(real, thresholds, side="left") / len(real)
    balanced = (recall_fake + recall_real) / 2
    feasible = (recall_fake >= minimum_recall) & (recall_real >= minimum_recall)
    eligible = np.flatnonzero(feasible) if feasible.any() else np.arange(len(thresholds))
    # Predeclared ranking: balanced accuracy, REAL recall, proximity to 0.5.
    order = np.lexsort((-np.abs(thresholds[eligible] - 0.5), recall_real[eligible], balanced[eligible]))
    best = int(eligible[order[-1]])
    selection = {"threshold": float(thresholds[best]), "split": split,
                 "criterion": "Maximize balanced accuracy subject to both class recalls >= minimum_recall; ties prefer higher Real recall then proximity to 0.5.",
                 "minimum_recall": minimum_recall, "recall_constraint_satisfied": bool(feasible[best]),
                 "fallback": "If no feasible threshold exists, maximize unconstrained balanced accuracy and mark candidate ineligible for promotion.",
                 "thresholds_evaluated": len(thresholds), "metrics": metrics(y, p, thresholds[best])}
    rows = [{"threshold": float(t), "balanced_accuracy": float(ba), "recall_fake": float(rf),
             "recall_real": float(rr), "feasible": bool(ok)}
            for t, ba, rf, rr, ok in zip(thresholds, balanced, recall_fake, recall_real, feasible)]
    return selection, rows


def publish_new(source, destination):
    """Atomically publish a complete file without ever replacing an existing one."""
    try:
        os.link(source, destination)  # Atomic exclusive creation on NTFS/POSIX.
    except FileExistsError:
        if evaluation.sha256_file(Path(source)) != evaluation.sha256_file(Path(destination)):
            raise ValueError(f"Refusing to replace different existing content: {destination}")


def save_json(path, payload):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, allow_nan=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        publish_new(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_csv(path, rows, fields=None):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        with temporary.open("x", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            f.flush()
            os.fsync(f.fileno())
        publish_new(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_evaluation(output, name, rows, probabilities, threshold):
    output = Path(output)
    marker = output / f"{name}_complete.json"
    identity = hashlib.sha256(json.dumps({"samples": [(r["path"], r["sha256"], r["label"]) for r in rows],
        "scores": [float(p) for p in probabilities], "threshold": float(threshold)}, sort_keys=True, allow_nan=False).encode()).hexdigest()
    if marker.exists():
        saved = json.loads(marker.read_text(encoding="utf-8"))
        if saved["input_sha256"] != identity:
            raise ValueError("Completed evaluation cannot be reused with different inputs")
        for filename, digest in saved["artifacts"].items():
            if evaluation.sha256_file(output / filename) != digest:
                raise ValueError(f"Evaluation artifact changed: {filename}")
        return json.loads((output / f"{name}_metrics.json").read_text(encoding="utf-8"))
    # Generate a whole bundle before exposing any output. An interrupted commit
    # can be resumed only when already-published files match exactly.
    with tempfile.TemporaryDirectory(prefix=f".{name}-", dir=output) as directory:
        staged = Path(directory)
        report = _write_evaluation(staged, name, rows, probabilities, threshold)
        artifacts = {}
        for source in staged.iterdir():
            destination = output / source.name
            digest = evaluation.sha256_file(source)
            if destination.exists():
                if evaluation.sha256_file(destination) != digest:
                    raise ValueError(f"Partial evaluation differs from fixed inputs: {source.name}")
            else:
                publish_new(source, destination)
            artifacts[source.name] = digest
        save_json(marker, {"input_sha256": identity, "artifacts": artifacts})
    return report


def _write_evaluation(output, name, rows, probabilities, threshold):
    y = np.asarray([r["label"] for r in rows])
    p = np.asarray(probabilities)
    report = metrics(y, p, threshold)
    report["score_distribution"] = {label: {"count": int((y == code).sum()),
        "quantiles_p_real": np.quantile(p[y == code], [0, .05, .25, .5, .75, .95, 1]).tolist()}
        for code, label in ((0, "Fake"), (1, "Real"))}
    save_json(output / f"{name}_metrics.json", report)
    predictions = []
    for row, score in zip(rows, p):
        predicted = int(score >= threshold)
        predictions.append({"path": row["path"], "sha256": row["sha256"], "label": row["label"],
                            "p_real": float(score), "p_fake": float(1-score), "prediction": predicted,
                            "threshold": threshold, "error": "correct" if predicted == row["label"] else
                            ("real_as_fake" if row["label"] else "fake_as_real")})
    save_csv(output / f"{name}_predictions.csv", predictions)
    # Curves use Fake as positive, consistent with FPR = genuine falsely flagged.
    fpr, tpr, roc_t = roc_curve(1-y, 1-p)
    precision, recall, pr_t = precision_recall_curve(1-y, 1-p)
    save_csv(output / f"{name}_roc.csv", [{"false_positive_rate": float(x), "true_positive_rate": float(z),
             "threshold_p_fake": float(t) if np.isfinite(t) else "infinity"} for x, z, t in zip(fpr, tpr, roc_t)])
    save_csv(output / f"{name}_precision_recall.csv", [{"recall": float(x), "precision": float(z),
             "threshold_p_fake": float(pr_t[i]) if i < len(pr_t) else "endpoint"} for i, (x, z) in enumerate(zip(recall, precision))])
    save_csv(output / f"{name}_confusion_matrix.csv", [
        {"actual": label, "predicted_fake": matrix[0], "predicted_real": matrix[1]}
        for label, matrix in zip(["Fake", "Real"], report["confusion_matrix"]["rows_actual_columns_predicted"])])
    plots = load_local("evaluation_plots")
    plots.curve(output / f"{name}_roc.svg", f"{name.replace('_', ' ').title()} ROC", fpr, tpr,
                "False positive rate (Real flagged Fake)", "Sensitivity (Fake recall)", f"{name}_roc.csv")
    plots.curve(output / f"{name}_precision_recall.svg", f"{name.replace('_', ' ').title()} precision–recall", recall, precision,
                "Recall (Fake)", "Precision (Fake)", f"{name}_precision_recall.csv")
    plots.confusion(output / f"{name}_confusion_matrix.svg", f"{name.replace('_', ' ').title()} confusion matrix",
                    report["confusion_matrix"]["rows_actual_columns_predicted"], f"{name}_confusion_matrix.csv")
    return report
