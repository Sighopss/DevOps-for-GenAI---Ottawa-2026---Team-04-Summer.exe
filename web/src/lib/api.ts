import { withDurations } from "@/lib/flight";
import type {
  AuditEvent,
  ErrorEnvelope,
  FlightDetail,
  FlightListItem,
  TraceSpanRecord,
} from "@/lib/types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function hasApiConfig(): boolean {
  return Boolean(apiBaseUrl);
}

function buildApiUrl(pathname: string): string {
  if (!apiBaseUrl) {
    throw new ApiError(500, "config", "NEXT_PUBLIC_API_URL is not configured.");
  }

  const base = apiBaseUrl.endsWith("/") ? apiBaseUrl : `${apiBaseUrl}/`;
  return new URL(pathname.replace(/^\//, ""), base).toString();
}

async function requestJson<T>(pathname: string, idToken: string): Promise<T> {
  const response = await fetch(buildApiUrl(pathname), {
    headers: {
      Authorization: `Bearer ${idToken}`,
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });
  const text = await response.text();
  const parsed = text ? (JSON.parse(text) as T | ErrorEnvelope) : null;

  if (!response.ok) {
    const envelope =
      parsed && typeof parsed === "object" && "error" in parsed
        ? (parsed as ErrorEnvelope)
        : { error: { code: "internal", message: "Request failed." } };
    throw new ApiError(response.status, envelope.error.code, envelope.error.message);
  }

  return parsed as T;
}

export async function fetchFlights(idToken: string): Promise<FlightListItem[]> {
  const body = await requestJson<{ flights: FlightListItem[] }>("v1/traces?limit=50", idToken);
  return body.flights;
}

export async function fetchFlightDetail(
  idToken: string,
  traceId: string,
): Promise<FlightDetail> {
  const body = await requestJson<{
    trace_id: string;
    tenant_id: FlightDetail["tenant_id"];
    expires_at: number;
    spans: TraceSpanRecord[];
  }>(`v1/traces/${traceId}`, idToken);

  return {
    trace_id: body.trace_id,
    tenant_id: body.tenant_id,
    expires_at: body.expires_at,
    spans: withDurations(body.spans),
  };
}

export async function fetchAuditEvents(
  idToken: string,
  traceId: string,
): Promise<AuditEvent[]> {
  const body = await requestJson<{ events: AuditEvent[] }>(
    `v1/traces/${traceId}/audit`,
    idToken,
  );
  return body.events;
}
