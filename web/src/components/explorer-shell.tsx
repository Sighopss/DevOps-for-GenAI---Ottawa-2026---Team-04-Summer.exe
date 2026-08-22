"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  ID_TOKEN_STORAGE_KEY,
  TENANT_STORAGE_KEY,
  persistIdTokenFromHash,
} from "@/lib/cognito";
import type {
  FlightFixture,
  FlightSummary,
  ForbiddenFixture,
  TraceSpan,
} from "@/lib/types";
import {
  formatCurrency,
  formatDuration,
  formatTimestamp,
  getRagHops,
  getSpanDepths,
  summarizeFlight,
  totalTokens,
} from "@/lib/flight";

type ExplorerShellProps = {
  flight: FlightFixture;
  forbidden: ForbiddenFixture;
  summary: FlightSummary;
};

type ExplorerContentProps = ExplorerShellProps & {
  selectedTraceId: string;
  onSelectTrace: (traceId: string) => void;
  selectedTenant: "tenant-a" | "tenant-b";
  onSelectTenant: (tenant: "tenant-a" | "tenant-b") => void;
};

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function KindBadge({ kind }: { kind: TraceSpan["kind"] }) {
  return <span className={`kind-badge kind-${kind}`}>{kind}</span>;
}

function ExplorerContent({
  flight,
  forbidden,
  summary,
  selectedTraceId,
  onSelectTrace,
  selectedTenant,
  onSelectTenant,
}: ExplorerContentProps) {
  const selectedSummary = useMemo(() => summarizeFlight(flight.spans), [flight.spans]);
  const depths = useMemo(() => getSpanDepths(flight.spans), [flight.spans]);
  const ragHops = useMemo(() => getRagHops(flight.spans), [flight.spans]);
  const isForbiddenState =
    selectedTenant === "tenant-b" && selectedTraceId === summary.traceId;
  const hasStoredToken =
    typeof window !== "undefined" &&
    Boolean(window.sessionStorage.getItem(ID_TOKEN_STORAGE_KEY));

  return (
    <main className="explorer-shell">
      <section className="explorer-topbar">
        <div>
          <p className="eyebrow">Explorer / Day 1 fixture</p>
          <h1>One flight. No raw prompt storage.</h1>
        </div>
        <div className="tenant-strip">
          <label className="tenant-switcher" htmlFor="tenant-switcher">
            <span>Tenant</span>
            <select
              id="tenant-switcher"
              onChange={(event) =>
                onSelectTenant(event.target.value as "tenant-a" | "tenant-b")
              }
              value={selectedTenant}
            >
              <option value="tenant-a">tenant-a</option>
              <option value="tenant-b">tenant-b</option>
            </select>
          </label>
          <span className="surface-badge">REDACTED</span>
          <span className="surface-badge">{selectedTenant}</span>
          <span className="surface-badge">TTL 7d</span>
          <span className="surface-badge">
            {hasStoredToken ? "ID token in session" : "Fixture mode"}
          </span>
        </div>
      </section>

      <div className="explorer-grid">
        <aside className="flight-list-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Flights</p>
              <h2>Signed-in list</h2>
            </div>
            <span className="count-pill">{selectedTenant === "tenant-a" ? "1 flight" : "0 flights"}</span>
          </div>
          {selectedTenant === "tenant-a" ? (
            <button
              className={`flight-row ${selectedTraceId === summary.traceId ? "is-active" : ""}`}
              onClick={() => onSelectTrace(summary.traceId)}
              type="button"
            >
              <div className="flight-row__header">
                <strong>{summary.traceId}</strong>
                <span>{summary.status}</span>
              </div>
              <p>{summary.promptPreview}</p>
              <dl className="flight-row__meta">
                <div>
                  <dt>Tenant</dt>
                  <dd>{summary.tenantId}</dd>
                </div>
                <div>
                  <dt>Duration</dt>
                  <dd>{formatDuration(summary.durationMs)}</dd>
                </div>
                <div>
                  <dt>Cost</dt>
                  <dd>{formatCurrency(summary.costUsd)}</dd>
                </div>
              </dl>
            </button>
          ) : (
            <div className="empty-state">
              <strong>No flights for tenant-b.</strong>
              <p>Tenant-scoped reads do not list tenant-a traces.</p>
            </div>
          )}
        </aside>

        <section className="detail-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Flight detail</p>
              <h2>Trace detail via `?trace_id=`</h2>
            </div>
            <span className="trace-chip">trace_id={selectedTraceId}</span>
          </div>

          <div className="summary-strip">
            <Stat label="Start" value={formatTimestamp(selectedSummary.startTime)} />
            <Stat label="End" value={formatTimestamp(selectedSummary.endTime)} />
            <Stat label="Tokens" value={String(totalTokens(flight.spans))} />
            <Stat label="Cost" value={formatCurrency(selectedSummary.costUsd)} />
          </div>

          {isForbiddenState ? (
            <section className="forbidden-panel">
              <p className="eyebrow">Contracted 403</p>
              <h3>
                {forbidden.expected_status} {forbidden.expected_body.error.code}
              </h3>
              <p className="forbidden-copy">{forbidden.expected_body.error.message}</p>
              <dl className="rag-hop__meta">
                <div>
                  <dt>Attempted trace</dt>
                  <dd>{selectedTraceId}</dd>
                </div>
                <div>
                  <dt>JWT tenant</dt>
                  <dd>{forbidden.request.jwt["custom:tenant_id"]}</dd>
                </div>
                <div>
                  <dt>Stored tenant</dt>
                  <dd>{forbidden.stored_tenant_id}</dd>
                </div>
              </dl>
            </section>
          ) : (
            <>
              <section className="waterfall-panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Waterfall</p>
                    <h3>Parent-child, latency, tokens, and cost</h3>
                  </div>
                </div>
                <div className="waterfall-table" role="table" aria-label="Flight waterfall">
                  {flight.spans.map((span) => {
                    const depth = depths.get(span.span_id) ?? 0;
                    const tokenCount =
                      (span["gen_ai.usage.input_tokens"] ?? 0) +
                      (span["gen_ai.usage.output_tokens"] ?? 0);

                    return (
                      <article className="waterfall-row" key={span.span_id} role="row">
                        <div
                          className="waterfall-row__span"
                          style={{ paddingInlineStart: `${depth * 20 + 12}px` }}
                        >
                          <KindBadge kind={span.kind} />
                          <div>
                            <strong>{span.name}</strong>
                            <p>{span.prompt_preview ?? "No prompt preview stored."}</p>
                          </div>
                        </div>
                        <span>{formatDuration(span.durationMs)}</span>
                        <span>{tokenCount > 0 ? tokenCount : "—"}</span>
                        <span>{formatCurrency(span.cost_usd)}</span>
                      </article>
                    );
                  })}
                </div>
              </section>

              <section className="rag-panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">RAG hops</p>
                    <h3>Masked query, document IDs, and scores</h3>
                  </div>
                </div>
                <div className="rag-list">
                  {ragHops.map((hop) => (
                    <article className="rag-hop" key={hop.spanId}>
                      <div className="rag-hop__query">
                        <span>Masked query</span>
                        <strong>{hop.maskedQuery}</strong>
                      </div>
                      <dl className="rag-hop__meta">
                        <div>
                          <dt>Document IDs</dt>
                          <dd>{hop.documentIds.join(", ") || "—"}</dd>
                        </div>
                        <div>
                          <dt>Scores</dt>
                          <dd>{hop.scores.length > 0 ? hop.scores.join(", ") : "—"}</dd>
                        </div>
                        <div>
                          <dt>Top K</dt>
                          <dd>{hop.topK ?? "—"}</dd>
                        </div>
                      </dl>
                    </article>
                  ))}
                </div>
              </section>
            </>
          )}
        </section>
      </div>
    </main>
  );
}

export function ExplorerShell({ flight, forbidden, summary }: ExplorerShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [selectedTenant, setSelectedTenant] = useState<"tenant-a" | "tenant-b">(
    "tenant-a",
  );

  const selectedTraceId = searchParams.get("trace_id") ?? summary.traceId;

  useEffect(() => {
    persistIdTokenFromHash();
    const storedTenant = window.sessionStorage.getItem(TENANT_STORAGE_KEY);

    if (storedTenant === "tenant-a" || storedTenant === "tenant-b") {
      setSelectedTenant(storedTenant);
    }
  }, []);

  const setTrace = (traceId: string) => {
    const next = new URLSearchParams(searchParams.toString());
    next.set("trace_id", traceId);
    router.replace(`${pathname}?${next.toString()}`);
  };

  const handleTenantChange = (tenant: "tenant-a" | "tenant-b") => {
    setSelectedTenant(tenant);
    window.sessionStorage.setItem(TENANT_STORAGE_KEY, tenant);
  };

  return (
    <ExplorerContent
      flight={flight}
      forbidden={forbidden}
      onSelectTrace={setTrace}
      onSelectTenant={handleTenantChange}
      selectedTraceId={selectedTraceId}
      selectedTenant={selectedTenant}
      summary={summary}
    />
  );
}

export function ExplorerShellFallback({
  flight,
  forbidden,
  summary,
}: ExplorerShellProps) {
  return (
    <ExplorerContent
      flight={flight}
      forbidden={forbidden}
      onSelectTrace={() => {}}
      onSelectTenant={() => {}}
      selectedTraceId={summary.traceId}
      selectedTenant="tenant-a"
      summary={summary}
    />
  );
}
