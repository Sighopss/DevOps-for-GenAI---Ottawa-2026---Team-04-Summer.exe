"""Corpus load + retrieve-only tool. No write/delete/shell."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

CORPUS_DIR = Path(__file__).resolve().parents[2] / "corpus"
RETRIEVE_TOP_K = 2
TOOL_NAME = "get_doc_metadata"


@dataclass
class Document:
    doc_id: str
    title: str
    path: Path
    text: str
    embedding: list[float] = field(default_factory=list)


def load_documents() -> list[Document]:
    root = CORPUS_DIR.resolve()
    if not root.is_dir():
        raise FileNotFoundError("corpus directory missing")
    docs: list[Document] = []
    for path in sorted(root.glob("*.md")):
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            continue
        text = resolved.read_text(encoding="utf-8")
        title = _title_from_markdown(text, resolved.stem)
        docs.append(
            Document(
                doc_id=f"doc-{resolved.stem}",
                title=title,
                path=resolved,
                text=text,
            )
        )
    if not docs:
        raise RuntimeError("corpus is empty")
    return docs


def get_doc_metadata(docs: list[Document], document_id: str) -> dict[str, Any]:
    """Allowlisted retrieve tool. Unknown ids and out-of-corpus paths fail closed."""
    root = CORPUS_DIR.resolve()
    for doc in docs:
        if doc.doc_id == document_id:
            resolved = doc.path.resolve()
            if not resolved.is_relative_to(root) or resolved.suffix != ".md":
                raise PermissionError("document is outside the allowlisted corpus")
            return {
                "document_id": doc.doc_id,
                "title": doc.title,
                "path": resolved.name,
                "chars": len(doc.text),
            }
    raise KeyError("unknown document")


Tool = Callable[[list[Document], str], dict[str, Any]]
TOOL_REGISTRY: Mapping[str, Tool] = MappingProxyType({TOOL_NAME: get_doc_metadata})


def retrieve_topk(docs: list[Document], query_embedding: list[float], k: int = RETRIEVE_TOP_K) -> list[Document]:
    ranked = sorted(docs, key=lambda doc: _cosine(query_embedding, doc.embedding), reverse=True)
    return ranked[: max(1, k)]


def _title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
