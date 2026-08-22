export type SpanKind = "http" | "llm" | "tool" | "rag";

export type TraceSpan = {
  trace_id: string;
  span_id: string;
  parent_id: string | null;
  tenant_id: string;
  kind: SpanKind;
  name: string;
  status: string;
  start_time: string;
  end_time: string;
  cost_usd: number;
  prompt_preview?: string;
  prompt_hash?: string;
  "gen_ai.request.model"?: string;
  "gen_ai.usage.input_tokens"?: number;
  "gen_ai.usage.output_tokens"?: number;
  attributes?: Record<string, unknown>;
  durationMs: number;
};

export type FlightFixture = {
  spans: TraceSpan[];
};

export type ForbiddenFixture = {
  description: string;
  request: {
    method: string;
    path: string;
    authorization: string;
    jwt: {
      username: string;
      "custom:tenant_id": string;
    };
  };
  stored_tenant_id: string;
  expected_status: number;
  expected_body: {
    error: {
      code: string;
      message: string;
    };
  };
};

export type FlightSummary = {
  traceId: string;
  tenantId: string;
  startTime: string;
  endTime: string;
  durationMs: number;
  costUsd: number;
  status: string;
  promptPreview: string;
};

export type RagHop = {
  spanId: string;
  maskedQuery: string;
  documentIds: string[];
  scores: string[];
  topK: number | null;
};
