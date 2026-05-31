"""Golden dataset loader. Source of truth = advisor-curated JSONL on disk."""

from __future__ import annotations

import json
from pathlib import Path

from shared.schemas import GoldenQuestion

DEFAULT_PATH = Path("data/golden_questions/golden.jsonl")


def load_golden(path: str | Path = DEFAULT_PATH) -> list[GoldenQuestion]:
    p = Path(path)
    if not p.exists():
        return []
    questions: list[GoldenQuestion] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        questions.append(GoldenQuestion.model_validate(json.loads(line)))
    return questions
