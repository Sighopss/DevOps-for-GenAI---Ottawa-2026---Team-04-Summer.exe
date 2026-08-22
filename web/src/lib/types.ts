export type TenantId = "tenant-a" | "tenant-b";

export type SpanKind = "http" | "llm" | "tool" | "rag";

export type TraceSpan = {
  trace_id: string;
  span_id: string;
  parent_id: string | null;
  tenant_id: TenantId;
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

export type TraceSpanRecord = Omit<TraceSpan, "durationMs">;

export type FlightListItem = {
  trace_id: string;
  tenant_id: TenantId;
  start_time: string;
  end_time: string;
  cost_usd: number;
  status: string;
  prompt_preview: string;
};

export type FlightDetail = {
  trace_id: string;
  tenant_id: TenantId;
  expires_at: number | null;
  spans: TraceSpan[];
};

export type AuditEvent = {
  actor: string;
  tenant_id: TenantId;
  trace_id: string;
  ts: string;
};

export type ForbiddenFixture = {
  description: string;
  request: {
    method: string;
    path: string;
    authorization: string;
    jwt: {
      username: string;
      "custom:tenant_id": TenantId;
    };
  };
  stored_tenant_id: TenantId;
  expected_status: number;
  expected_body: {
    error: {
      code: string;
      message: string;
    };
  };
  spans: TraceSpan[];
};

export type ErrorEnvelope = {
  error: {
    code: string;
    message: string;
  };
};

export type FixtureDataset = {
  flightsByTenant: Record<TenantId, FlightListItem[]>;
  detailsByTenant: Record<TenantId, Record<string, FlightDetail>>;
  forbidden: ForbiddenFixture;
};

export type FlightSummary = {
  traceId: string;
  tenantId: TenantId;
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
