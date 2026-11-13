from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CORPUS_FILE = DATA_DIR / "web_training_corpus.json"


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _empty_corpus() -> dict[str, Any]:
    return {
        "updated_at": "",
        "sources_count": 0,
        "docs": [],
    }


def load_training_corpus(path: Path = CORPUS_FILE) -> dict[str, Any]:
    if not path.exists():
        return _empty_corpus()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_corpus()
    if not isinstance(data, dict):
        return _empty_corpus()
    docs = data.get("docs")
    if not isinstance(docs, list):
        docs = []
    return {
        "updated_at": str(data.get("updated_at") or ""),
        "sources_count": int(data.get("sources_count") or len(docs)),
        "docs": [doc for doc in docs if isinstance(doc, dict)],
    }


def collect_training_corpus(path: Path = CORPUS_FILE) -> dict[str, Any]:
    """Return the local web corpus without doing network work during app startup.

    The self-trained model can use web/public training docs when they exist, but
    the backend should still boot cleanly when that optional corpus has not been
    generated yet.
    """
    corpus = load_training_corpus(path)
    if corpus.get("updated_at"):
        return corpus
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    corpus = {
        "updated_at": _now_text(),
        "sources_count": 0,
        "docs": [],
    }
    path.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")
    return corpus
