import fs from "node:fs";
import path from "node:path";
import {
  flightListItemFromSpans,
  withDurations,
} from "@/lib/flight";
import type {
  FixtureDataset,
  FlightDetail,
  ForbiddenFixture,
  TenantId,
  TraceSpanRecord,
} from "@/lib/types";

function readFixtureJson<T>(filename: string): T {
  const fixturePath = path.join(process.cwd(), "..", "contracts", "fixtures", filename);
  return JSON.parse(fs.readFileSync(fixturePath, "utf-8")) as T;
}

function detailFromSpans(spans: ReturnType<typeof withDurations>): FlightDetail {
  const root = spans[0];

  return {
    trace_id: root.trace_id,
    tenant_id: root.tenant_id,
    expires_at: null,
    spans,
  };
}

export function loadFixtureData(): FixtureDataset {
  const tenantA = readFixtureJson<{ spans: TraceSpanRecord[] }>("tenant-a-rag.json");
  const tenantB = readFixtureJson<Omit<ForbiddenFixture, "spans"> & { spans: TraceSpanRecord[] }>(
    "tenant-b-forbidden.json",
  );
  const tenantASpans = withDurations(tenantA.spans);
  const tenantBSpans = withDurations(tenantB.spans);
  const tenantADetail = detailFromSpans(tenantASpans);
  const tenantBDetail = detailFromSpans(tenantBSpans);

  return {
    flightsByTenant: {
      "tenant-a": [flightListItemFromSpans(tenantASpans)],
      "tenant-b": [flightListItemFromSpans(tenantBSpans)],
    },
    detailsByTenant: {
      "tenant-a": { [tenantADetail.trace_id]: tenantADetail },
      "tenant-b": { [tenantBDetail.trace_id]: tenantBDetail },
    },
    forbidden: {
      ...tenantB,
      spans: tenantBSpans,
    },
  };
}

export function getFixtureDefaultTraceId(
  fixtures: FixtureDataset,
  tenantId: TenantId,
): string | null {
  return fixtures.flightsByTenant[tenantId][0]?.trace_id ?? null;
}
