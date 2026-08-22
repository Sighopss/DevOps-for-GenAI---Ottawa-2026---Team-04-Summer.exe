"""Bedrock embeddings + converse, or a documented fake when TRACEVAULT_FAKE_BEDROCK=1."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config

from demo_app.rag import Document

CONNECT_TIMEOUT_S = 5
READ_TIMEOUT_S = 30
MAX_OUTPUT_TOKENS = 256
FAKE_EMBED_DIM = 64
FAKE_INPUT_TOKENS = 1
FAKE_OUTPUT_TOKENS = 1
FAKE_COST_USD = 0.0


@dataclass
class ConverseResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


def fake_bedrock_enabled() -> bool:
    return os.environ.get("TRACEVAULT_FAKE_BEDROCK", "").strip() == "1"


def embed_texts(texts: list[str]) -> list[list[float]]:
    if fake_bedrock_enabled():
        return [_fake_embed(text) for text in texts]
    client = _runtime_client()
    model = os.environ.get("BEDROCK_EMBED_MODEL_ID", "").strip()
    if not model:
        raise RuntimeError("BEDROCK_EMBED_MODEL_ID is required unless TRACEVAULT_FAKE_BEDROCK=1")
    return [_invoke_embed(client, model, text) for text in texts]


def converse(*, question: str, context: str) -> ConverseResult:
    model = os.environ.get("BEDROCK_MODEL_ID", "").strip() or "fake-bedrock"
    if fake_bedrock_enabled():
        return ConverseResult(
            text=_fake_answer(context),
            model=model,
            input_tokens=FAKE_INPUT_TOKENS,
            output_tokens=FAKE_OUTPUT_TOKENS,
            cost_usd=FAKE_COST_USD,
        )
    if not os.environ.get("BEDROCK_MODEL_ID", "").strip():
        raise RuntimeError("BEDROCK_MODEL_ID is required unless TRACEVAULT_FAKE_BEDROCK=1")
    client = _runtime_client()
    response = client.converse(
        modelId=model,
        messages=[
            {
                "role": "user",
                "content": [{"text": f"{question}\n\nAnswer from this corpus only:\n{context}"}],
            }
        ],
        inferenceConfig={"maxTokens": MAX_OUTPUT_TOKENS, "temperature": 0},
    )
    text = _converse_text(response)
    usage = response.get("usage") or {}
    return ConverseResult(
        text=text,
        model=model,
        input_tokens=int(usage.get("inputTokens") or 0),
        output_tokens=int(usage.get("outputTokens") or 0),
        cost_usd=0.0,
    )


def _runtime_client() -> Any:
    region = os.environ.get("AWS_REGION", "").strip() or "us-east-1"
    cfg = Config(
        connect_timeout=CONNECT_TIMEOUT_S,
        read_timeout=READ_TIMEOUT_S,
        retries={"max_attempts": 1},
    )
    return boto3.client("bedrock-runtime", region_name=region, config=cfg)


def _invoke_embed(client: Any, model: str, text: str) -> list[float]:
    raw = client.invoke_model(
        modelId=model,
        body=json.dumps({"inputText": text}),
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(raw["body"].read())
    embedding = payload.get("embedding")
    if not isinstance(embedding, list):
        raise RuntimeError("bedrock embed response missing embedding")
    return [float(v) for v in embedding]


def _converse_text(response: dict[str, Any]) -> str:
    message = response.get("output", {}).get("message", {})
    parts = message.get("content") or []
    chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
    return "".join(chunks).strip() or "(empty)"


def _fake_embed(text: str) -> list[float]:
    vec = [0.0] * FAKE_EMBED_DIM
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        vec[digest[0] % FAKE_EMBED_DIM] += 1.0
    return vec


def _fake_answer(context: str) -> str:
    snippet = " ".join(context.split())[:400]
    return f"From the corpus: {snippet}"


def attach_embeddings(docs: list[Document]) -> None:
    vectors = embed_texts([doc.text for doc in docs])
    for doc, vector in zip(docs, vectors, strict=True):
        doc.embedding = vector
