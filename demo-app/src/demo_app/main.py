"""CLI: one retrieve tool, one converse, four nested spans, exit 0."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

from demo_app.bedrock import attach_embeddings, converse, embed_texts, fake_bedrock_enabled
from demo_app.emitter import load_emitter
from demo_app.rag import RETRIEVE_TOP_K, TOOL_NAME, get_doc_metadata, load_documents, retrieve_topk

log = logging.getLogger("demo_app")

PII_PREFIX = "Contact user@example.com SSN 123-45-6789. "
_TENANTS = ("tenant-a", "tenant-b")


def run(*, question: str, tenant_id: str, pii: bool) -> tuple[str, list[dict[str, Any]]]:
    if tenant_id not in _TENANTS:
        raise ValueError("tenant_id must be tenant-a or tenant-b")
    user_text = f"{PII_PREFIX}{question}" if pii else question
    client, start_span = load_emitter(tenant_id)
    docs = load_documents()
    answer = ""
    try:
        with start_span(
            client,
            kind="http",
            name="demo.ask",
            attributes={"route": "/ask"},
        ):
            attach_embeddings(docs)
            query_vec = embed_texts([user_text])[0]
            with start_span(
                client,
                kind="rag",
                name="demo.retrieve",
                attributes={"rag.top_k": RETRIEVE_TOP_K},
            ):
                hits = retrieve_topk(docs, query_vec, k=RETRIEVE_TOP_K)
            top = hits[0]
            with start_span(
                client,
                kind="tool",
                name="demo.get_doc_metadata",
                attributes={
                    "tool.name": TOOL_NAME,
                    "tool.document_id": top.doc_id,
                },
            ):
                get_doc_metadata(docs, top.doc_id)
            context = "\n\n".join(doc.text for doc in hits)
            model = os.environ.get("BEDROCK_MODEL_ID", "").strip() or (
                "fake-bedrock" if fake_bedrock_enabled() else ""
            )
            with start_span(
                client,
                kind="llm",
                name="demo.converse",
                model=model or None,
                sensitive=pii,
                prompt=user_text if pii else None,
            ) as llm_span:
                result = converse(question=user_text, context=context)
                llm_span.set_usage(
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    cost_usd=result.cost_usd,
                )
                answer = result.text
    finally:
        client.flush()
    return answer, list(client.spans)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="TraceVault demo RAG/agent (one retrieve tool)")
    parser.add_argument("--question", required=True)
    parser.add_argument("--tenant", default="tenant-a", choices=_TENANTS)
    parser.add_argument(
        "--pii",
        action="store_true",
        help="Prepend synthetic email/SSN and mark the llm span sensitive=True. Prompt is never logged.",
    )
    args = parser.parse_args(argv)
    if args.pii:
        log.info("running with --pii (prompt not logged)")
    answer, _spans = run(question=args.question, tenant_id=args.tenant, pii=args.pii)
    print(answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
