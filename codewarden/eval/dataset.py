"""Load the Golden Dataset: a small synthetic repo with hand-labeled
ground truth for which (rule, file) pairs are genuine violations.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from codewarden.parsing.model import ParsedFile
from codewarden.parsing.parser import parse_source

REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "eval" / "golden_dataset" / "repo"
LABELS_PATH = Path(__file__).resolve().parent.parent.parent / "eval" / "golden_dataset" / "labels.yaml"


@dataclass
class GoldenDataset:
    parsed_files: dict[str, ParsedFile]
    labels: dict[str, dict[str, bool]]  # rule_id -> {relative_path: violates}


def load_golden_dataset() -> GoldenDataset:
    parsed_files: dict[str, ParsedFile] = {}
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in (".py", ".ts"):
            continue
        rel_path = str(path.relative_to(REPO_ROOT))
        parsed_files[rel_path] = parse_source(rel_path, path.read_text())

    labels_data = yaml.safe_load(LABELS_PATH.read_text())
    labels = {rule_id: dict(file_labels) for rule_id, file_labels in labels_data["rules"].items()}

    return GoldenDataset(parsed_files=parsed_files, labels=labels)
