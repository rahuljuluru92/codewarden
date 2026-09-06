"""Precision/recall/F1 over (rule_id, file_path) ground-truth pairs.

This is deliberately simple binary classification at file granularity
("does this file violate this rule, yes or no") rather than
line-level matching, since that's the granularity the Golden Dataset is
labeled at (see DECISIONS.md, Stage 5 entry, for why).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvalResult:
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return (2 * p * r / (p + r)) if (p + r) else 0.0

    def as_dict(self) -> dict:
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
        }


def score(predicted: dict[tuple[str, str], bool], ground_truth: dict[tuple[str, str], bool]) -> EvalResult:
    """predicted/ground_truth: {(rule_id, file_path): violates_bool}, same key set."""
    tp = fp = fn = tn = 0
    for key, actual in ground_truth.items():
        pred = predicted.get(key, False)
        if pred and actual:
            tp += 1
        elif pred and not actual:
            fp += 1
        elif not pred and actual:
            fn += 1
        else:
            tn += 1
    return EvalResult(true_positives=tp, false_positives=fp, false_negatives=fn, true_negatives=tn)
