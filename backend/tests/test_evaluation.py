"""Evaluation-tool tests using generated fixture pixels and stub model scores only.

These tests do NOT estimate the saved detector's accuracy or run real evaluation.
All datasets, fake model bytes, and output reports are isolated in pytest tmp_path.
"""
import csv
import importlib.util
import json
from pathlib import Path
import shutil
import sys

from PIL import Image
import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "evaluate.py"
SPEC = importlib.util.spec_from_file_location("evaluation_tool_under_test", TOOL)
evaluation = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = evaluation
SPEC.loader.exec_module(evaluation)


@pytest.fixture
def dataset(tmp_path):
    root = tmp_path / "dataset"
    index = 0
    for split in ("Train", "Validation", "Test"):
        for label in ("Fake", "Real"):
            directory = root / split / label
            directory.mkdir(parents=True)
            for number in range(3):
                index += 1
                Image.new("RGB", (5, 4), (index * 11, index * 7, index * 3)).save(directory / f"fixture-{number}.png")
    return root


@pytest.fixture
def artifacts(tmp_path):
    directory = tmp_path / "model-artifacts"
    directory.mkdir()
    model = directory / "fixture.keras"
    model.write_bytes(b"not-a-real-model; test prediction factory is stubbed")
    threshold = directory / "threshold.json"
    threshold.write_text('{"threshold": 0.42}', encoding="utf-8")
    return model, threshold


def arguments(dataset, artifacts, output, command="evaluate", extra=()):
    model, threshold = artifacts
    return evaluation.build_parser().parse_args([
        command, "--dataset-root", str(dataset), "--model", str(model),
        "--threshold-file", str(threshold), "--output-dir", str(output), *extra,
    ])


def fixture_predictor_factory(model_path, seed):
    assert model_path.name == "fixture.keras"
    assert seed == 42

    def predict(samples, batch_size):
        assert batch_size == 8
        # Deliberately label-based scores ONLY for exercising report mechanics.
        return [0.1 if sample.label == 0 else 0.9 for sample in samples]
    return predict


def test_confusion_rates_and_threshold_equality():
    result = evaluation.metrics([0, 0, 1, 1], [0.10, 0.42, 0.41, 0.90], 0.42)
    assert result["confusion_matrix"]["rows_actual_columns_predicted"] == [[1, 1], [1, 1]]
    for name in ("accuracy", "precision_fake", "recall_fake", "f1_fake", "precision_real", "recall_real", "f1_real", "balanced_accuracy", "false_positive_rate_real_as_fake", "false_negative_rate_fake_as_real"):
        assert result[name] == pytest.approx(0.5)
    assert result["roc_auc_real_positive"] == pytest.approx(0.75)
    assert result["counts"]["false_positive_real_as_fake"] == 1


def test_auc_ties_and_undefined_metrics():
    assert evaluation.metrics([0, 1], [0.5, 0.5], 0.42)["roc_auc_real_positive"] == 0.5
    result = evaluation.metrics([1, 1], [0.9, 0.8], 0.42)
    assert result["recall_fake"] is None
    assert result["precision_fake"] is None
    assert result["false_negative_rate_fake_as_real"] is None
    assert result["roc_auc_real_positive"] is None
    assert result["balanced_accuracy"] is None
    assert result["false_positive_rate_real_as_fake"] == 0
    assert result["false_positive_rate_wilson_95"][1] > 0
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), -0.1, 1.1, True, "0.42", None])
def test_invalid_threshold_rejected(threshold):
    with pytest.raises(evaluation.EvaluationError):
        evaluation.metrics([0, 1], [0.1, 0.9], threshold)


@pytest.mark.parametrize("labels,scores", [([], []), ([0], []), ([2], [0.2]), ([True], [0.2]), ([0], [float("nan")]), ([1], [1.1])])
def test_invalid_metric_inputs_rejected(labels, scores):
    with pytest.raises(evaluation.EvaluationError):
        evaluation.metrics(labels, scores, 0.42)


def test_scan_explicit_labels_and_all_splits(dataset):
    samples = evaluation.scan_dataset(dataset)
    assert len(samples) == 18
    assert {s.split for s in samples} == {"train", "validation", "test"}
    assert all(s.label == {"Fake": 0, "Real": 1}[s.label_name] for s in samples)
    assert len({s.sha256 for s in samples}) == 18
    assert all(Path(s.path).is_absolute() and s.bytes > 0 for s in samples)


def test_lowercase_split_aliases_supported(dataset):
    # Rename via intermediate names to work on case-insensitive Windows filesystems.
    for original, replacement in (("Train", "train"), ("Validation", "valid"), ("Test", "test")):
        temporary = dataset / (original + "-temporary")
        (dataset / original).rename(temporary)
        temporary.rename(dataset / replacement)
    assert len(evaluation.scan_dataset(dataset)) == 18


def test_unknown_or_missing_split_rejected(dataset):
    (dataset / "Validation").rename(dataset / "holdout")
    with pytest.raises(evaluation.EvaluationError, match="Unknown split"):
        evaluation.scan_dataset(dataset)


@pytest.mark.parametrize("destination,reason", [
    ("Test/Fake/copied.png", "split overlap"),
    ("Test/Real/copied.png", "contradictory labels"),
    ("Train/Fake/copied.png", "duplicate image"),
])
def test_duplicate_content_rejected_across_entire_inventory(dataset, destination, reason):
    shutil.copyfile(dataset / "Train/Fake/fixture-0.png", dataset / destination)
    with pytest.raises(evaluation.EvaluationError, match=reason):
        evaluation.scan_dataset(dataset)


def test_unsupported_files_are_not_silently_omitted(dataset):
    (dataset / "Test/Real/unsupported.bmp").write_bytes(b"fixture")
    with pytest.raises(evaluation.EvaluationError, match="JPG/JPEG/PNG/WEBP"):
        evaluation.scan_dataset(dataset)


def test_balanced_subset_reproducible_without_resplitting(dataset):
    samples = evaluation.scan_dataset(dataset)
    selected = evaluation.select_samples(samples, "test", 2, 42)
    assert selected == evaluation.select_samples(list(reversed(samples)), "test", 2, 42)
    assert len(selected) == 4
    assert all(sample.split == "test" for sample in selected)
    assert sum(sample.label == 0 for sample in selected) == 2
    with pytest.raises(evaluation.EvaluationError, match="has 3"):
        evaluation.select_samples(samples, "test", 4, 42)
    with pytest.raises(evaluation.EvaluationError, match="positive"):
        evaluation.select_samples(samples, "test", 0, 42)


def test_fixed_threshold_report_provenance_and_preserved_inputs(dataset, artifacts, tmp_path):
    before = {path: evaluation.sha256_file(path) for path in [*dataset.rglob("*.png"), *artifacts]}
    output = tmp_path / "test-report"
    args = arguments(dataset, artifacts, output)
    report = evaluation.run_evaluation(args, fixture_predictor_factory)
    assert report["metrics"]["threshold_real"] == 0.42
    assert report["metrics"]["samples"] == 6
    assert report["metrics"]["accuracy"] == 1.0  # Stub behavior, NOT detector accuracy.
    assert {path.name for path in output.iterdir()} == {"manifest.json", "evaluation.json", "predictions.csv"}
    manifest = json.loads((output / "manifest.json").read_text())
    assert len(manifest["inventory"]) == 18
    assert len(manifest["selected_paths"]) == 6
    assert manifest["provenance"]["label_mapping"] == {"Fake": 0, "Real": 1}
    assert manifest["provenance"]["artifacts"]["model"]["sha256"] == before[artifacts[0]]
    assert manifest["provenance"]["artifacts"]["preprocessing"]["sha256"]
    assert "packages" in manifest["provenance"]["environment"]
    with (output / "predictions.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 6
    assert all(row["split"] == "test" for row in rows)
    assert {row["ground_truth"] for row in rows} == {"Fake", "Real"}
    assert all(float(row["p_real"]) + float(row["p_fake"]) == pytest.approx(1) for row in rows)
    assert before == {path: evaluation.sha256_file(path) for path in before}


def test_prediction_rows_identify_false_positives_and_negatives(dataset):
    samples = evaluation.select_samples(evaluation.scan_dataset(dataset), "test", 1, 42)
    probabilities = [0.42 if s.label == 0 else 0.41 for s in samples]
    rows = evaluation.prediction_rows(samples, probabilities, 0.42)
    assert {row["error_type"] for row in rows} == {"false_positive_real_as_fake", "false_negative_fake_as_real"}


def test_validation_alternatives_are_separate_and_never_change_threshold(dataset, artifacts, tmp_path):
    before = artifacts[1].read_bytes()
    output = tmp_path / "validation-report"
    args = arguments(dataset, artifacts, output, "validation-thresholds", ("--thresholds", "0.3", "0.42", "0.5"))
    evaluation.run_evaluation(args, fixture_predictor_factory)
    alternative = json.loads((output / "validation_thresholds.json").read_text())
    assert alternative["split"] == "validation"
    assert alternative["fixed_saved_threshold"] == 0.42
    assert [m["threshold_real"] for m in alternative["alternatives"]] == [0.3, 0.42, 0.5]
    assert artifacts[1].read_bytes() == before
    assert not (output / "threshold.json").exists()
    assert all("Validation" in path for path in json.loads((output / "manifest.json").read_text())["selected_paths"])


def test_test_split_threshold_tuning_rejected(dataset, artifacts, tmp_path):
    args = arguments(dataset, artifacts, tmp_path / "forbidden", "validation-thresholds", ("--thresholds", "0.5"))
    args.split = "test"
    with pytest.raises(evaluation.EvaluationError, match="only on validation"):
        evaluation.run_evaluation(args, fixture_predictor_factory)
    assert not args.output_dir.exists()
    with pytest.raises(SystemExit):
        evaluation.build_parser().parse_args(["evaluate", "--dataset-root", str(dataset), "--output-dir", str(tmp_path / "out"), "--thresholds", "0.5"])


def test_outputs_cannot_overwrite_or_enter_dataset_or_model(dataset, artifacts, tmp_path):
    for output in (dataset / "new-report", artifacts[0].parent / "new-report", artifacts[1], dataset):
        with pytest.raises(evaluation.EvaluationError):
            evaluation.run_evaluation(arguments(dataset, artifacts, output), fixture_predictor_factory)
    output = tmp_path / "already-exists"
    output.mkdir()
    with pytest.raises(evaluation.EvaluationError, match="already exists"):
        evaluation.run_evaluation(arguments(dataset, artifacts, output), fixture_predictor_factory)


def test_missing_dataset_creates_no_output_or_model_load(artifacts, tmp_path):
    output = tmp_path / "no-results"
    args = arguments(tmp_path / "missing-dataset", artifacts, output)
    def must_not_load(*args):
        pytest.fail("Model must not load without a valid dataset")
    with pytest.raises(FileNotFoundError):
        evaluation.run_evaluation(args, must_not_load)
    assert not output.exists()


def test_changed_artifact_aborts_before_outputs(dataset, artifacts, tmp_path):
    output = tmp_path / "changed-artifact-report"
    def changing_factory(model_path, seed):
        artifacts[1].write_text('{"threshold": 0.5}')
        return fixture_predictor_factory(model_path, seed)
    with pytest.raises(evaluation.EvaluationError, match="changed during evaluation"):
        evaluation.run_evaluation(arguments(dataset, artifacts, output), changing_factory)
    assert not output.exists()


def test_collect_and_evaluate_known_manifest(dataset, artifacts, tmp_path):
    real = dataset / "Test/Real/fixture-0.png"
    fake = dataset / "Test/Fake/fixture-0.png"
    manifest = tmp_path / "known.json"
    evaluation.collect_known([real], [fake], "Generated pytest fixtures, not real ground-truth evaluation", manifest)
    samples, metadata = evaluation.read_known(manifest)
    assert len(samples) == 2
    assert {s.split for s in samples} == {"known"}
    assert "operator-supplied" in metadata["label_status"]
    args = evaluation.build_parser().parse_args([
        "evaluate", "--known-manifest", str(manifest), "--model", str(artifacts[0]),
        "--threshold-file", str(artifacts[1]), "--output-dir", str(tmp_path / "known-report"),
    ])
    result = evaluation.run_evaluation(args, fixture_predictor_factory)
    assert result["provenance"]["split"] == "known"
    assert "not a held-out" in result["evaluation_scope"]
    with pytest.raises(evaluation.EvaluationError, match="already exists"):
        evaluation.collect_known([real], [fake], "fixtures", manifest)


def test_known_manifest_detects_changed_images_and_conflicting_labels(dataset, tmp_path):
    image = dataset / "Test/Real/fixture-0.png"
    with pytest.raises(evaluation.EvaluationError, match="contradictory labels"):
        evaluation.collect_known([image], [image], "fixtures", tmp_path / "conflict.json")
    manifest = tmp_path / "known.json"
    evaluation.collect_known([image], [], "fixtures", manifest)
    Image.new("RGB", (5, 4), (255, 255, 255)).save(image)
    with pytest.raises(evaluation.EvaluationError, match="changed since collection"):
        evaluation.read_known(manifest)


def test_main_missing_dataset_fails_cleanly(tmp_path, capsys):
    assert evaluation.main(["evaluate", "--dataset-root", str(tmp_path / "missing"), "--output-dir", str(tmp_path / "no-output")]) == 2
    assert "Evaluation refused" in capsys.readouterr().err
    assert not (tmp_path / "no-output").exists()
