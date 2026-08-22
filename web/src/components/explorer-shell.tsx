"use client";

import { startTransition, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  ID_TOKEN_STORAGE_KEY,
  TENANT_STORAGE_KEY,
  persistIdTokenFromHash,
  readIdTokenIdentity,
  readStoredIdToken,
} from "@/lib/cognito";
import { ApiError, fetchAuditEvents, fetchFlightDetail, fetchFlights, hasApiConfig } from "@/lib/api";
import type {
  AuditEvent,
  FixtureDataset,
  FlightDetail,
  FlightListItem,
  FlightSummary,
  TenantId,
  TraceSpan,
} from "@/lib/types";
import {
  formatAuditTimestamp,
  formatCurrency,
  formatDuration,
  formatTimestamp,
  formatTtl,
  findPrimaryModel,
  getRagHops,
  getSpanErrorMessage,
  getSpanDepths,
  summarizeFlight,
  summarizeFlightItem,
  totalTokens,
} from "@/lib/flight";

const EMPTY_SPANS: TraceSpan[] = [];

function getDefaultFixtureTraceId(
  fixtures: FixtureDataset,
  tenant: TenantId,
): string | null {
  return fixtures.flightsByTenant[tenant][0]?.trace_id ?? null;
}

type ExplorerShellProps = {
  fixtures: FixtureDataset;
};

type RequestFailure = {
  status: number | null;
  code: string | null;
  message: string;
};

type ExplorerContentProps = {
  auditError: string | null;
  auditEvents: AuditEvent[];
  detailFailure: RequestFailure | null;
  detailStatus: "idle" | "loading" | "ready" | "forbidden" | "error";
  fixtureForbiddenTraceId: string;
  flights: FlightListItem[];
  fixtures: FixtureDataset;
  listFailure: RequestFailure | null;
  liveMode: boolean;
  onSelectTrace: (traceId: string) => void;
  onSelectTenant: (tenant: TenantId) => void;
  selectedDetail: FlightDetail | null;
  selectedSummary: FlightSummary | null;
  selectedTenant: TenantId;
  selectedTraceId: string | null;
  signedInTenant: TenantId | null;
  switcherDisabled: boolean;
};

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value || "—"}</strong>
    </div>
  );
}

function KindBadge({ kind }: { kind: TraceSpan["kind"] }) {
  return <span className={`kind-badge kind-${kind}`}>{kind}</span>;
}

function getFailureCopy(
  failure: RequestFailure | null,
  scope: "list" | "detail",
): { title: string; copy: string } {
  if (!failure) {
    return scope === "list"
      ? {
          title: "Live list unavailable.",
          copy: "The signed-in list could not be loaded.",
        }
      : {
          title: "Trace detail unavailable.",
          copy: "The trace detail could not be loaded.",
        };
  }

  if (failure.code === "unreachable") {
    return scope === "list"
      ? {
          title: "API unreachable.",
          copy: "Could not reach GET /v1/traces*. Check NEXT_PUBLIC_API_URL and the read API deployment.",
        }
      : {
          title: "API unreachable.",
          copy: "Could not reach the read API for detail or audit. Check NEXT_PUBLIC_API_URL and the live read deployment.",
        };
  }

  if (failure.status === 404 || failure.code === "not_found") {
    return {
      title: "Trace not found.",
      copy: "This trace_id was not returned for the signed-in tenant.",
    };
  }

  const statusLabel = failure.status ? `${failure.status} ` : "";
  const codeLabel = failure.code ? `${failure.code}: ` : "";

  return scope === "list"
    ? {
        title: "Live list unavailable.",
        copy: `${statusLabel}${codeLabel}${failure.message}`.trim(),
      }
    : {
        title: "Trace detail unavailable.",
        copy: `${statusLabel}${codeLabel}${failure.message}`.trim(),
      };
}

function ExplorerContent({
  auditError,
  auditEvents,
  detailFailure,
  detailStatus,
  fixtureForbiddenTraceId,
  flights,
  fixtures,
  listFailure,
  liveMode,
  selectedTraceId,
  onSelectTrace,
  selectedDetail,
  selectedSummary,
  selectedTenant,
  onSelectTenant,
  signedInTenant,
  switcherDisabled,
}: ExplorerContentProps) {
  const detailSpans = useMemo(() => selectedDetail?.spans ?? EMPTY_SPANS, [selectedDetail]);
  const depths = useMemo(() => getSpanDepths(detailSpans), [detailSpans]);
  const ragHops = useMemo(() => getRagHops(detailSpans), [detailSpans]);
  const modelName = useMemo(() => findPrimaryModel(detailSpans), [detailSpans]);
  const maxDuration = useMemo(() => {
    return detailSpans.reduce((max, span) => Math.max(max, span.durationMs), 0);
  }, [detailSpans]);
  const isForbiddenState =
    detailStatus === "forbidden" ||
    (!liveMode &&
      selectedTenant === "tenant-b" &&
      selectedTraceId === fixtureForbiddenTraceId);
  const hasStoredToken =
    typeof window !== "undefined" &&
    Boolean(window.sessionStorage.getItem(ID_TOKEN_STORAGE_KEY));
  const sourceLabel = liveMode ? "Day 2 live GET /v1/traces*" : "Day 1 fixture only";
  const forbidden = fixtures.forbidden;
  const hasSignedInTenant = Boolean(signedInTenant);
  const noFlightsCopy = liveMode
    ? "No flights returned for the signed-in tenant yet."
    : selectedTenant === "tenant-b"
      ? "Day 1 keeps tenant-a-rag.json as the only regular fixture. Tenant-b only gets the locked 403 contract example."
      : "Day 1 uses contracts/fixtures/tenant-a-rag.json only.";
  const selectedTraceDisplay = selectedTraceId ?? "pending";
  const detailFailureCopy = getFailureCopy(detailFailure, "detail");
  const listFailureCopy = getFailureCopy(listFailure, "list");

  return (
    <main className="explorer-shell">
      <section className="explorer-topbar">
        <div>
          <p className="eyebrow">Explorer / {sourceLabel}</p>
          <h1>One flight. No raw prompt storage.</h1>
        </div>
        <div className="tenant-strip">
          <label className="tenant-switcher" htmlFor="tenant-switcher">
            <span>Tenant</span>
            <select
              disabled={switcherDisabled}
              id="tenant-switcher"
              onChange={(event) =>
                onSelectTenant(event.target.value as TenantId)
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
            {hasStoredToken ? "ID token in sessionStorage" : "No live token yet"}
          </span>
          <span className="surface-badge">
            {liveMode ? "Live read active" : "Fixture mode"}
          </span>
        </div>
        <p className="topbar-helper">
          {liveMode
            ? hasSignedInTenant
              ? `Live reads follow the signed-in ID token for ${signedInTenant}. Re-authenticate to switch live tenants.`
              : "Live API URL is present, but the stored token has no tenant claim. Use the Cognito ID token, not the access token."
            : "Demo integrity: Day 1 stays on committed fixtures until a valid ID token and API URL are present."}
        </p>
      </section>

      <div className="explorer-grid">
        <aside className="flight-list-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Flights</p>
              <h2>Signed-in list</h2>
            </div>
            <span className="count-pill">
              {flights.length === 1 ? "1 flight" : `${flights.length} flights`}
            </span>
          </div>
          {listFailure ? (
            <div className="empty-state">
              <strong>{listFailureCopy.title}</strong>
              <p>{listFailureCopy.copy}</p>
            </div>
          ) : flights.length > 0 ? (
            <>
              {flights.map((flight) => {
                const summary = summarizeFlightItem(flight);

                return (
                  <button
                    className={`flight-row ${
                      selectedTraceId === summary.traceId ? "is-active" : ""
                    }`}
                    key={summary.traceId}
                    onClick={() => onSelectTrace(summary.traceId)}
                    type="button"
                  >
                    <div className="flight-row__header">
                      <strong>{summary.traceId}</strong>
                      <span>{summary.status}</span>
                    </div>
                    <p className="masked-preview">
                      <span className="inline-redacted">REDACTED</span>
                      {summary.promptPreview}
                    </p>
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
                );
              })}
            </>
          ) : (
            <div className="empty-state">
              <strong>No flights to display.</strong>
              <p>{noFlightsCopy}</p>
            </div>
          )}
          {!liveMode && selectedTenant === "tenant-b" ? (
            <button
              className={`flight-row flight-row--ghost ${
                selectedTraceId === fixtureForbiddenTraceId ? "is-active" : ""
              }`}
              onClick={() => onSelectTrace(fixtureForbiddenTraceId)}
              type="button"
            >
              <div className="flight-row__header">
                <strong>{fixtureForbiddenTraceId}</strong>
                <span>forbidden</span>
              </div>
              <p>Locked contract example: tenant-b asks for a tenant-a trace and must see 403, not 404.</p>
            </button>
          ) : null}
        </aside>

        <section className="detail-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Flight detail</p>
              <h2>Trace detail via `?trace_id=`</h2>
            </div>
            <span className="trace-chip">trace_id={selectedTraceDisplay}</span>
          </div>

          {isForbiddenState ? (
            <section className="forbidden-panel">
              <p className="eyebrow">{liveMode ? "Live 403" : "Contracted 403"}</p>
              <h3>
                {liveMode && detailFailure
                  ? `403 ${detailFailure.message}`
                  : `${forbidden.expected_status} ${forbidden.expected_body.error.code}`}
              </h3>
              <p className="forbidden-copy">
                {liveMode && detailFailure
                  ? `${detailFailure.code ?? "forbidden"}: ${detailFailure.message}`
                  : forbidden.expected_body.error.message}
              </p>
              <dl className="rag-hop__meta">
                <div>
                  <dt>Attempted trace</dt>
                  <dd>{selectedTraceDisplay}</dd>
                </div>
                <div>
                  <dt>JWT tenant</dt>
                  <dd>{signedInTenant ?? forbidden.request.jwt["custom:tenant_id"]}</dd>
                </div>
                <div>
                  <dt>Stored tenant</dt>
                  <dd>{forbidden.stored_tenant_id}</dd>
                </div>
              </dl>
            </section>
          ) : detailStatus === "loading" ? (
            <section className="empty-state">
              <strong>Loading trace detail.</strong>
              <p>Fetching list/detail/audit through the read contract.</p>
            </section>
          ) : detailStatus === "error" ? (
            <section className="empty-state">
              <strong>{detailFailureCopy.title}</strong>
              <p>{detailFailureCopy.copy}</p>
            </section>
          ) : !selectedDetail || !selectedSummary ? (
            <section className="empty-state">
              <strong>No trace selected yet.</strong>
              <p>Choose a flight from the list to reconstruct one request.</p>
            </section>
          ) : (
            <>
              <div className="summary-strip">
                <Stat label="Started" value={formatTimestamp(selectedSummary.startTime)} />
                <Stat label="Latency" value={formatDuration(selectedSummary.durationMs)} />
                <Stat label="Model" value={modelName} />
                <Stat label="Tokens" value={String(totalTokens(detailSpans))} />
                <Stat label="Cost USD" value={formatCurrency(selectedSummary.costUsd)} />
                <Stat label="TTL" value={formatTtl(selectedDetail.expires_at)} />
              </div>

              <section className="waterfall-panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Waterfall</p>
                    <h3>Parent-child, latency, tokens, and cost</h3>
                  </div>
                </div>
                <div className="waterfall-table" role="table" aria-label="Flight waterfall">
                  {detailSpans.map((span) => {
                    const depth = depths.get(span.span_id) ?? 0;
                    const tokenCount =
                      (span["gen_ai.usage.input_tokens"] ?? 0) +
                      (span["gen_ai.usage.output_tokens"] ?? 0);
                    const errorMessage =
                      span.status === "error" ? getSpanErrorMessage(span) ?? "Span failed." : null;
                    const latencyWidth =
                      maxDuration > 0
                        ? `${Math.max((span.durationMs / maxDuration) * 100, 8)}%`
                        : "0%";

                    return (
                      <article
                        className={`waterfall-row ${span.status === "error" ? "is-error" : ""}`}
                        key={span.span_id}
                        role="row"
                      >
                        <div
                          className="waterfall-row__span"
                          style={{ paddingInlineStart: `${depth * 20 + 12}px` }}
                        >
                          <KindBadge kind={span.kind} />
                          <div>
                            <strong>{span.name}</strong>
                            <p className="masked-preview">
                              <span className="inline-redacted">REDACTED</span>
                              {span.prompt_preview ?? "No prompt preview stored."}
                            </p>
                            <p className="waterfall-row__meta-line">
                              <span>Status {span.status}</span>
                              {span["gen_ai.request.model"] ? (
                                <span>Model {span["gen_ai.request.model"]}</span>
                              ) : null}
                            </p>
                            {errorMessage ? (
                              <p className="waterfall-row__error">{errorMessage}</p>
                            ) : null}
                          </div>
                        </div>
                        <div className="waterfall-row__latency">
                          <div className="latency-meter" aria-hidden="true">
                            <span style={{ width: latencyWidth }} />
                          </div>
                          <strong>{formatDuration(span.durationMs)}</strong>
                        </div>
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
                        <strong>
                          <span className="inline-redacted">REDACTED</span>
                          {hop.maskedQuery}
                        </strong>
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

              <section className="audit-panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Audit trail</p>
                    <h3>Audit / tenant strip</h3>
                  </div>
                </div>
                {liveMode ? (
                  auditError ? (
                    <div className="empty-state compact-state">
                      <strong>Audit fetch failed.</strong>
                      <p>{auditError}</p>
                    </div>
                  ) : auditEvents.length > 0 ? (
                    <div className="audit-list">
                      {auditEvents.map((event) => (
                        <article className="audit-row" key={`${event.actor}-${event.ts}`}>
                          <div>
                            <strong>{event.actor}</strong>
                            <p>{formatAuditTimestamp(event.ts)}</p>
                          </div>
                          <dl className="audit-row__meta">
                            <div>
                              <dt>Tenant</dt>
                              <dd>{event.tenant_id}</dd>
                            </div>
                            <div>
                              <dt>Trace</dt>
                              <dd>{event.trace_id}</dd>
                            </div>
                          </dl>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state compact-state">
                      <strong>Audit row pending.</strong>
                      <p>The live route writes an audit row on GET detail/audit, then returns it here.</p>
                    </div>
                  )
                ) : (
                  <div className="empty-state compact-state">
                    <strong>Fixture mode does not invent audit rows.</strong>
                    <p>Day 2 live GET `/v1/traces/{'{trace_id}'}/audit` writes and returns tenant-scoped events.</p>
                  </div>
                )}
              </section>
            </>
          )}
        </section>
      </div>
    </main>
  );
}

export function ExplorerShell({ fixtures }: ExplorerShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isClientReady, setIsClientReady] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<TenantId>("tenant-a");
  const [idToken, setIdToken] = useState<string | null>(null);
  const [liveFlights, setLiveFlights] = useState<FlightListItem[]>([]);
  const [listFailure, setListFailure] = useState<RequestFailure | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<FlightDetail | null>(null);
  const [detailStatus, setDetailStatus] = useState<
    "idle" | "loading" | "ready" | "forbidden" | "error"
  >("idle");
  const [detailFailure, setDetailFailure] = useState<RequestFailure | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [auditError, setAuditError] = useState<string | null>(null);
  const selectedTraceId = searchParams.get("trace_id");
  const signedInIdentity = useMemo(() => readIdTokenIdentity(idToken), [idToken]);
  const signedInTenant = signedInIdentity.tenantId;
  const fixtureForbiddenTraceId = useMemo(() => {
    return fixtures.forbidden.request.path.split("/").pop() ?? "";
  }, [fixtures.forbidden.request.path]);
  const liveMode = hasApiConfig() && Boolean(idToken);
  const fixtureFlights = fixtures.flightsByTenant[selectedTenant];
  const activeFlights = liveMode ? liveFlights : fixtureFlights;

  const selectedSummary = useMemo(() => {
    if (selectedDetail) {
      return summarizeFlight(selectedDetail.spans);
    }

    const currentFlight = activeFlights.find((flight) => flight.trace_id === selectedTraceId);
    return currentFlight ? summarizeFlightItem(currentFlight) : null;
  }, [activeFlights, selectedDetail, selectedTraceId]);

  useEffect(() => {
    persistIdTokenFromHash();
    const token = readStoredIdToken();
    setIdToken(token);
    const storedTenant = window.sessionStorage.getItem(TENANT_STORAGE_KEY);
    const storedIdentity = readIdTokenIdentity(token);

    if (storedIdentity.tenantId) {
      setSelectedTenant(storedIdentity.tenantId);
      window.sessionStorage.setItem(TENANT_STORAGE_KEY, storedIdentity.tenantId);
      setIsClientReady(true);
      return;
    }

    if (storedTenant === "tenant-a" || storedTenant === "tenant-b") {
      setSelectedTenant(storedTenant);
    }

    setIsClientReady(true);
  }, []);

  useEffect(() => {
    let cancelled = false;

    if (!liveMode || !idToken) {
      setLiveFlights([]);
      setListFailure(null);
      return () => {
        cancelled = true;
      };
    }

    setListFailure(null);

    fetchFlights(idToken)
      .then((flights) => {
        if (cancelled) {
          return;
        }
        setLiveFlights(flights);
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        if (error instanceof ApiError) {
          setListFailure({
            status: error.status,
            code: error.code,
            message: error.message,
          });
          return;
        }
        setListFailure({
          status: null,
          code: "unreachable",
          message: "Live list fetch failed.",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [idToken, liveMode]);

  useEffect(() => {
    if (!isClientReady) {
      return;
    }

    const defaultTraceId = liveMode
      ? liveFlights[0]?.trace_id ?? null
      : selectedTenant === "tenant-b"
        ? fixtureForbiddenTraceId
        : getDefaultFixtureTraceId(fixtures, selectedTenant);
    const fixtureTraceStillValid =
      !selectedTraceId ||
      Boolean(fixtures.detailsByTenant[selectedTenant][selectedTraceId]) ||
      (selectedTenant === "tenant-b" && selectedTraceId === fixtureForbiddenTraceId);

    if (
      defaultTraceId &&
      (!selectedTraceId || (!liveMode && !fixtureTraceStillValid))
    ) {
      const next = new URLSearchParams(searchParams.toString());
      next.set("trace_id", defaultTraceId);
      startTransition(() => {
        router.replace(`${pathname}?${next.toString()}`);
      });
    }
  }, [
    fixtureForbiddenTraceId,
    fixtures,
    isClientReady,
    liveFlights,
    liveMode,
    pathname,
    router,
    searchParams,
    selectedTenant,
    selectedTraceId,
  ]);

  useEffect(() => {
    if (!liveMode) {
      setDetailStatus("ready");
      setDetailFailure(null);
      setAuditError(null);
      setAuditEvents([]);

      if (!selectedTraceId) {
        setSelectedDetail(null);
        return;
      }

      const fixtureDetail = fixtures.detailsByTenant[selectedTenant][selectedTraceId] ?? null;
      setSelectedDetail(fixtureDetail);
      return;
    }

    if (!idToken || !selectedTraceId) {
      setSelectedDetail(null);
      setDetailStatus("idle");
      return;
    }

    let cancelled = false;
    setDetailStatus("loading");
    setDetailFailure(null);
    setAuditError(null);
    setAuditEvents([]);

    fetchFlightDetail(idToken, selectedTraceId)
      .then((detail) => {
        if (cancelled) {
          return;
        }
        setSelectedDetail(detail);
        setDetailStatus("ready");
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setSelectedDetail(null);
        if (error instanceof ApiError) {
          setDetailStatus(error.status === 403 ? "forbidden" : "error");
          setDetailFailure({
            status: error.status,
            code: error.code,
            message: error.message,
          });
          return;
        }
        setDetailStatus("error");
        setDetailFailure({
          status: null,
          code: "unreachable",
          message: "Live detail fetch failed.",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [fixtures, idToken, liveMode, selectedTenant, selectedTraceId]);

  useEffect(() => {
    if (!liveMode || !idToken || !selectedTraceId || detailStatus !== "ready") {
      return;
    }

    let cancelled = false;
    setAuditError(null);

    fetchAuditEvents(idToken, selectedTraceId)
      .then((events) => {
        if (cancelled) {
          return;
        }
        setAuditEvents(events);
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        if (error instanceof ApiError) {
          setAuditError(`${error.code}: ${error.message}`);
          return;
        }
        setAuditError("Live audit fetch failed.");
      });

    return () => {
      cancelled = true;
    };
  }, [detailStatus, idToken, liveMode, selectedTraceId]);

  const setTrace = (traceId: string) => {
    const next = new URLSearchParams(searchParams.toString());
    next.set("trace_id", traceId);
    startTransition(() => {
      router.replace(`${pathname}?${next.toString()}`);
    });
  };

  const handleTenantChange = (tenant: TenantId) => {
    setSelectedTenant(tenant);
    window.sessionStorage.setItem(TENANT_STORAGE_KEY, tenant);
  };

  return (
    <ExplorerContent
      auditError={auditError}
      auditEvents={auditEvents}
      detailFailure={detailFailure ?? listFailure}
      detailStatus={listFailure ? "error" : detailStatus}
      fixtureForbiddenTraceId={fixtureForbiddenTraceId}
      flights={activeFlights}
      fixtures={fixtures}
      listFailure={listFailure}
      liveMode={liveMode}
      onSelectTrace={setTrace}
      onSelectTenant={handleTenantChange}
      selectedDetail={selectedDetail}
      selectedSummary={selectedSummary}
      selectedTraceId={selectedTraceId}
      selectedTenant={selectedTenant}
      signedInTenant={signedInTenant}
      switcherDisabled={liveMode && Boolean(signedInTenant)}
    />
  );
}

export function ExplorerShellFallback({ fixtures }: ExplorerShellProps) {
  const selectedTenant: TenantId = "tenant-a";
  const selectedTraceId = getDefaultFixtureTraceId(fixtures, selectedTenant);
  const selectedDetail = selectedTraceId
    ? fixtures.detailsByTenant[selectedTenant][selectedTraceId]
    : null;
  const selectedSummary = selectedDetail ? summarizeFlight(selectedDetail.spans) : null;

  return (
    <ExplorerContent
      auditError={null}
      auditEvents={[]}
      detailFailure={null}
      detailStatus="ready"
      fixtureForbiddenTraceId={fixtures.forbidden.request.path.split("/").pop() ?? ""}
      flights={fixtures.flightsByTenant[selectedTenant]}
      fixtures={fixtures}
      listFailure={null}
      liveMode={false}
      onSelectTrace={() => {}}
      onSelectTenant={() => {}}
      selectedDetail={selectedDetail}
      selectedSummary={selectedSummary}
      selectedTraceId={selectedTraceId}
      selectedTenant={selectedTenant}
      signedInTenant={null}
      switcherDisabled={false}
    />
  );
}
