import type {
  FlightListItem,
  FlightSummary,
  RagHop,
  TraceSpan,
  TraceSpanRecord,
} from "@/lib/types";

export function withDurations(spans: TraceSpanRecord[]): TraceSpan[] {
  return spans.map((span) => {
    const start = new Date(span.start_time).getTime();
    const end = new Date(span.end_time).getTime();

    return {
      ...span,
      durationMs: Math.max(end - start, 0),
    };
  });
}

export function summarizeFlight(spans: TraceSpan[]): FlightSummary {
  const sorted = [...spans].sort(
    (left, right) =>
      new Date(left.start_time).getTime() - new Date(right.start_time).getTime(),
  );
  const root = sorted[0];
  const startTime = root.start_time;
  const endTime = sorted.reduce((latest, span) => {
    return new Date(span.end_time).getTime() > new Date(latest).getTime()
      ? span.end_time
      : latest;
  }, root.end_time);
  const costUsd = spans.reduce((sum, span) => sum + span.cost_usd, 0);
  const promptPreview =
    spans.find((span) => span.prompt_preview)?.prompt_preview ?? "No masked preview stored.";

  return {
    traceId: root.trace_id,
    tenantId: root.tenant_id,
    startTime,
    endTime,
    durationMs: Math.max(new Date(endTime).getTime() - new Date(startTime).getTime(), 0),
    costUsd,
    status: root.status,
    promptPreview,
  };
}

export function summarizeFlightItem(item: FlightListItem): FlightSummary {
  return {
    traceId: item.trace_id,
    tenantId: item.tenant_id,
    startTime: item.start_time,
    endTime: item.end_time,
    durationMs: Math.max(
      new Date(item.end_time).getTime() - new Date(item.start_time).getTime(),
      0,
    ),
    costUsd: item.cost_usd,
    status: item.status,
    promptPreview: item.prompt_preview,
  };
}

export function flightListItemFromSpans(spans: TraceSpan[]): FlightListItem {
  const summary = summarizeFlight(spans);

  return {
    trace_id: summary.traceId,
    tenant_id: summary.tenantId,
    start_time: summary.startTime,
    end_time: summary.endTime,
    cost_usd: summary.costUsd,
    status: summary.status,
    prompt_preview: summary.promptPreview,
  };
}

export function totalTokens(spans: TraceSpan[]): number {
  return spans.reduce((sum, span) => {
    return sum + (span["gen_ai.usage.input_tokens"] ?? 0) + (span["gen_ai.usage.output_tokens"] ?? 0);
  }, 0);
}

export function getSpanDepths(spans: TraceSpan[]): Map<string, number> {
  const byId = new Map(spans.map((span) => [span.span_id, span]));
  const depths = new Map<string, number>();

  const resolveDepth = (span: TraceSpan): number => {
    if (depths.has(span.span_id)) {
      return depths.get(span.span_id) ?? 0;
    }
    if (!span.parent_id) {
      depths.set(span.span_id, 0);
      return 0;
    }

    const parent = byId.get(span.parent_id);
    const depth = parent ? resolveDepth(parent) + 1 : 0;
    depths.set(span.span_id, depth);
    return depth;
  };

  spans.forEach(resolveDepth);
  return depths;
}

export function getRagHops(spans: TraceSpan[]): RagHop[] {
  return spans
    .filter((span) => span.kind === "rag")
    .map((span) => {
      const documentIds = Array.isArray(span.attributes?.["rag.document_ids"])
        ? (span.attributes?.["rag.document_ids"] as string[])
        : [];
      const scores = Array.isArray(span.attributes?.["rag.scores"])
        ? (span.attributes?.["rag.scores"] as number[]).map((score) =>
            score.toFixed(2),
          )
        : [];

      return {
        spanId: span.span_id,
        maskedQuery: span.prompt_preview ?? "No masked query stored.",
        documentIds,
        scores,
        topK:
          typeof span.attributes?.["rag.top_k"] === "number"
            ? (span.attributes["rag.top_k"] as number)
            : null,
      };
    });
}

export function formatDuration(durationMs: number): string {
  if (durationMs < 1000) {
    return `${durationMs} ms`;
  }

  return `${(durationMs / 1000).toFixed(2)} s`;
}

export function formatCurrency(costUsd: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 4,
    maximumFractionDigits: 4,
  }).format(costUsd);
}

export function formatTimestamp(timestamp: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(timestamp));
}

export function formatAuditTimestamp(timestamp: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(timestamp));
}
