from codewarden.eval.dataset import load_golden_dataset
from codewarden.eval.harness import build_predicted, validate_labels_cover_scope
from codewarden.eval.metrics import score
from codewarden.rules.loader import load_ruleset
from codewarden.eval.harness import RULES_PATH


def test_metrics_score_perfect_match():
    ground_truth = {("r1", "a.py"): True, ("r1", "b.py"): False}
    predicted = {("r1", "a.py"): True, ("r1", "b.py"): False}
    result = score(predicted, ground_truth)
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1 == 1.0
    assert result.true_negatives == 1


def test_metrics_score_with_false_positive_and_false_negative():
    ground_truth = {("r1", "a.py"): True, ("r1", "b.py"): False, ("r1", "c.py"): True}
    predicted = {("r1", "a.py"): True, ("r1", "b.py"): True, ("r1", "c.py"): False}
    result = score(predicted, ground_truth)
    assert result.true_positives == 1
    assert result.false_positives == 1
    assert result.false_negatives == 1
    assert round(result.precision, 4) == 0.5
    assert round(result.recall, 4) == 0.5


def test_metrics_score_handles_zero_predictions_without_division_error():
    ground_truth = {("r1", "a.py"): True}
    predicted: dict = {}
    result = score(predicted, ground_truth)
    assert result.precision == 0.0
    assert result.recall == 0.0
    assert result.f1 == 0.0


def test_golden_dataset_loads_all_fixture_files():
    dataset = load_golden_dataset()
    assert len(dataset.parsed_files) == 13
    assert "controllers/user_controller.py" in dataset.parsed_files
    assert "services/emailService.ts" in dataset.parsed_files


def test_golden_dataset_labels_cover_every_applicable_rule_file_pair():
    dataset = load_golden_dataset()
    ruleset = load_ruleset(RULES_PATH)
    # should not raise
    validate_labels_cover_scope(dataset, ruleset)


def test_build_predicted_marks_unflagged_files_as_no_violation():
    ruleset = load_ruleset(RULES_PATH)
    dataset = load_golden_dataset()
    empty_report = {"findings": []}
    predicted = build_predicted(empty_report, ruleset, dataset)
    assert predicted[("no-controller-db-access", "controllers/user_controller.py")] is False


def test_build_predicted_marks_confirmed_findings_as_violations():
    ruleset = load_ruleset(RULES_PATH)
    dataset = load_golden_dataset()
    report = {
        "findings": [
            {
                "rule_id": "no-controller-db-access",
                "file_path": "controllers/order_controller.py",
                "status": "confirmed",
            }
        ]
    }
    predicted = build_predicted(report, ruleset, dataset)
    assert predicted[("no-controller-db-access", "controllers/order_controller.py")] is True
