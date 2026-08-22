"""Agent/tool authorization and budget evidence for handbook §3."""

from __future__ import annotations

import ast
import os
import socket
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

import pytest

import demo_app.bedrock as bedrock
import demo_app.main as app
from demo_app.rag import Document, TOOL_NAME, TOOL_REGISTRY, get_doc_metadata, load_documents


def test_registry_is_exactly_one_immutable_retrieve_tool() -> None:
    assert tuple(TOOL_REGISTRY) == ("get_doc_metadata",)
    assert TOOL_NAME == "get_doc_metadata"
    assert TOOL_REGISTRY[TOOL_NAME] is get_doc_metadata
    with pytest.raises(TypeError):
        TOOL_REGISTRY["write_file"] = get_doc_metadata  # type: ignore[index]


def test_tool_cannot_reach_write_delete_shell_or_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs = load_documents()

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("read-only tool reached a forbidden capability")

    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "unlink", forbidden)
    monkeypatch.setattr(os, "remove", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)

    result = TOOL_REGISTRY[TOOL_NAME](docs, docs[0].doc_id)
    assert result["document_id"] == docs[0].doc_id
    assert set(result) == {"document_id", "title", "path", "chars"}


def test_tool_rejects_document_outside_corpus(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("# not allowlisted", encoding="utf-8")
    document = Document(doc_id="doc-outside", title="outside", path=outside, text="secret")
    with pytest.raises(PermissionError, match="outside the allowlisted corpus"):
        TOOL_REGISTRY[TOOL_NAME]([document], document.doc_id)


def test_agent_has_no_loop_and_calls_converse_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRACEVAULT_FAKE_BEDROCK", "1")
    monkeypatch.delenv("TRACEVAULT_INGEST_URL", raising=False)
    calls = 0
    original = app.converse

    def counted(**kwargs: str) -> bedrock.ConverseResult:
        nonlocal calls
        calls += 1
        return original(**kwargs)

    monkeypatch.setattr(app, "converse", counted)
    app.run(question="What is retained?", tenant_id="tenant-a", pii=False)

    source = Path(app.__file__).read_text(encoding="utf-8")
    run_node = next(
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "run"
    )
    assert not any(isinstance(node, (ast.For, ast.AsyncFor, ast.While)) for node in ast.walk(run_node))
    assert app.MAX_AGENT_ITERATIONS == 1
    assert calls == app.MAX_AGENT_ITERATIONS


def test_bedrock_timeout_retry_and_token_budgets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class Client:
        def converse(self, **kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return {
                "output": {"message": {"content": [{"text": "bounded"}]}},
                "usage": {"inputTokens": 2, "outputTokens": 1},
            }

    def client_factory(_service: str, **kwargs: Any) -> Client:
        captured["config"] = kwargs["config"]
        return Client()

    monkeypatch.delenv("TRACEVAULT_FAKE_BEDROCK", raising=False)
    monkeypatch.setenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
    monkeypatch.setattr(bedrock.boto3, "client", client_factory)

    result = bedrock.converse(question="q", context="c")
    config = captured["config"]
    assert result.text == "bounded"
    assert captured["inferenceConfig"] == {
        "maxTokens": bedrock.MAX_OUTPUT_TOKENS,
        "temperature": 0,
    }
    assert bedrock.MAX_OUTPUT_TOKENS == 256
    assert config.connect_timeout == bedrock.CONNECT_TIMEOUT_S == 5
    assert config.read_timeout == bedrock.READ_TIMEOUT_S == 30
    assert config.retries["max_attempts"] == 1


def test_live_converse_computes_nonzero_cost_usd_from_real_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Issue #118: the live path must not hardcode cost_usd=0.0."""

    class Client:
        def converse(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "output": {"message": {"content": [{"text": "answer"}]}},
                "usage": {"inputTokens": 612, "outputTokens": 143},
            }

    monkeypatch.delenv("TRACEVAULT_FAKE_BEDROCK", raising=False)
    monkeypatch.setenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
    monkeypatch.setattr(bedrock.boto3, "client", lambda *_a, **_k: Client())

    result = bedrock.converse(question="q", context="c")
    assert result.input_tokens == 612
    assert result.output_tokens == 143
    assert result.cost_usd > 0.0
    assert result.cost_known is True
    assert "amazon.nova-lite-v1:0" in result.cost_note


def test_fake_bedrock_cost_stays_zero_and_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRACEVAULT_FAKE_BEDROCK", "1")
    result = bedrock.converse(question="q", context="c")
    assert result.cost_usd == 0.0
    assert result.cost_known is True
    assert "TRACEVAULT_FAKE_BEDROCK" in result.cost_note


def test_converse_rejects_model_outside_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TRACEVAULT_FAKE_BEDROCK", raising=False)
    monkeypatch.setenv("BEDROCK_MODEL_ID", "amazon.titan-text-express-v1")
    with pytest.raises(RuntimeError, match="not in the agreed allowlist"):
        bedrock.converse(question="q", context="c")


def test_live_defaults_are_agreed_models(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class Client:
        def converse(self, **kwargs: Any) -> dict[str, Any]:
            captured["modelId"] = kwargs["modelId"]
            return {
                "output": {"message": {"content": [{"text": "ok"}]}},
                "usage": {"inputTokens": 1, "outputTokens": 1},
            }

        def invoke_model(self, **kwargs: Any) -> dict[str, Any]:
            captured["embedModelId"] = kwargs["modelId"]

            class Body:
                def read(self) -> bytes:
                    return b'{"embedding":[0.1,0.2]}'

            return {"body": Body()}

    monkeypatch.delenv("TRACEVAULT_FAKE_BEDROCK", raising=False)
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    monkeypatch.delenv("BEDROCK_EMBED_MODEL_ID", raising=False)
    monkeypatch.setattr(bedrock.boto3, "client", lambda *_a, **_k: Client())

    result = bedrock.converse(question="q", context="c")
    vectors = bedrock.embed_texts(["hello"])
    assert result.model == bedrock.DEFAULT_CONVERSE_MODEL_ID
    assert captured["modelId"] == bedrock.DEFAULT_CONVERSE_MODEL_ID
    assert captured["embedModelId"] == bedrock.DEFAULT_EMBED_MODEL_ID
    assert vectors == [[0.1, 0.2]]
