"use client";

import Image from "next/image";
import { startTransition, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  completeHostedUiSignIn,
  readIdTokenIdentity,
  readStoredIdToken,
  TENANT_STORAGE_KEY,
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
  findPrimaryModel,
  formatAuditTimestamp,
  formatCurrency,
  formatDuration,
  formatTimestamp,
  formatTtl,
  getRagHops,
  getSpanDepths,
  getSpanErrorMessage,
  summarizeFlight,
  summarizeFlightItem,
  totalTokens,
} from "@/lib/flight";

const EMPTY_SPANS: TraceSpan[] = [];
const EXPLORER_PATH = "/explorer/";

type DetailStatus = "idle" | "loading" | "ready" | "forbidden" | "error";

type RequestFailure = {
  status: number | null;
  code: string | null;
  message: string;
};

type ExplorerShellProps = {
  fixtures: FixtureDataset;
};

type ExplorerContentProps = {
  auditError: string | null;
  auditEvents: AuditEvent[];
  authError: string | null;
  detailFailure: RequestFailure | null;
  detailStatus: DetailStatus;
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

function getDefaultFixtureTraceId(fixtures: FixtureDataset, tenant: TenantId): string | null {
  return fixtures.flightsByTenant[tenant][0]?.trace_id ?? null;
}

function TraceVaultBrand({ compact = false }: { compact?: boolean }) {
  return (
    <Image
      alt="TraceVault enterprise mark"
      className={`brand-mark ${compact ? "brand-mark--compact" : ""}`}
      height={4608}
      src="/tracevault-enterprise.png"
      unoptimized
      width={3072}
    />
  );
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
          title: "Selected flight unavailable.",
          copy: "The selected trace could not be reconstructed.",
        };
  }

  if (failure.code === "unreachable") {
    return scope === "list"
      ? {
          title: "API unreachable.",
          copy: "Could not reach GET /v1/traces*. Check the live read deployment.",
        }
      : {
          title: "Selected flight unavailable.",
          copy: "Could not reach the read API for detail or audit.",
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
        title: "Selected flight unavailable.",
        copy: `${statusLabel}${codeLabel}${failure.message}`.trim(),
      };
}

function ExplorerContent({
  auditError,
  auditEvents,
  authError,
  detailFailure,
  detailStatus,
  fixtureForbiddenTraceId,
  flights,
  fixtures,
  listFailure,
  liveMode,
  onSelectTrace,
  onSelectTenant,
  selectedDetail,
  selectedSummary,
  selectedTenant,
  selectedTraceId,
  signedInTenant,
  switcherDisabled,
}: ExplorerContentProps) {
  const detailSpans = useMemo(() => selectedDetail?.spans ?? EMPTY_SPANS, [selectedDetail]);
  const depths = useMemo(() => getSpanDepths(detailSpans), [detailSpans]);
  const ragHops = useMemo(() => getRagHops(detailSpans), [detailSpans]);
  const modelName = useMemo(() => findPrimaryModel(detailSpans), [detailSpans]);
  const tokenCount = useMemo(() => totalTokens(detailSpans), [detailSpans]);
  const firstPromptHash = useMemo(() => {
    return detailSpans.find((span) => typeof span.prompt_hash === "string")?.prompt_hash ?? null;
  }, [detailSpans]);
  const firstPromptPreview = useMemo(() => {
    return detailSpans.find((span) => span.prompt_preview)?.prompt_preview ?? "No masked preview stored.";
  }, [detailSpans]);
  const rootStartMs = useMemo(() => {
    return detailSpans.length > 0
      ? Math.min(...detailSpans.map((span) => new Date(span.start_time).getTime()))
      : 0;
  }, [detailSpans]);
  const totalTimelineMs = useMemo(() => {
    if (detailSpans.length === 0) {
      return 0;
    }

    const start = Math.min(...detailSpans.map((span) => new Date(span.start_time).getTime()));
    const end = Math.max(...detailSpans.map((span) => new Date(span.end_time).getTime()));
    return Math.max(end - start, 1);
  }, [detailSpans]);
  const listFailureCopy = getFailureCopy(listFailure, "list");
  const detailFailureCopy = getFailureCopy(detailFailure, "detail");
  const selectedTraceDisplay = selectedTraceId ?? "pending";
  const summary = selectedSummary;
  const hasSessionToken = Boolean(signedInTenant) || liveMode;
  const modeLabel = liveMode ? "Live tenant read" : "Committed fixture replay";
  const listTitle = liveMode ? "Flight list" : "Fixture flights";
  const noFlightsCopy = liveMode
    ? "No flights returned for the signed-in tenant yet."
    : selectedTenant === "tenant-b"
      ? "Tenant-b only gets the locked 403 contract example on Day 1."
      : "Day 1 uses contracts/fixtures/tenant-a-rag.json only.";
  const isForbiddenState =
    detailStatus === "forbidden" ||
    (!liveMode &&
      selectedTenant === "tenant-b" &&
      selectedTraceId === fixtureForbiddenTraceId);
  const forbidden = fixtures.forbidden;
  const signedInModeCopy = liveMode
    ? signedInTenant
      ? `Signed in as ${signedInTenant}. Reads stay tenant-scoped through the ID token.`
      : "Live mode is enabled, but the stored token does not expose a tenant claim."
    : "Fixture mode stays honest: one committed tenant-a flight, one locked tenant-b isolation proof.";
  const liveAuditCopy =
    "Live audit reads answer who opened the trace, when, and which tenant context applied.";

  return (
    <main className="explorer-shell">
      <section className="explorer-topbar">
        <div className="brand-cluster">
          <TraceVaultBrand compact />
          <div className="brand-copy">
            <p className="eyebrow">{modeLabel}</p>
            <p className="explorer-purpose">
              Reconstruct one request fast: waterfall, hops, spend, redaction, and
              isolation on one operator surface.
            </p>
            <p className="explorer-limitation">{signedInModeCopy}</p>
          </div>
        </div>

        <div className="operate-band">
          <div className="tenant-band">
            <label className="tenant-switcher" htmlFor="tenant-switcher">
              <span>Tenant</span>
              <select
                disabled={switcherDisabled}
                id="tenant-switcher"
                onChange={(event) => onSelectTenant(event.target.value as TenantId)}
                value={selectedTenant}
              >
                <option value="tenant-a">tenant-a</option>
                <option value="tenant-b">tenant-b</option>
              </select>
            </label>
            <span className="surface-badge surface-badge--accent">REDACTED</span>
            <span className="surface-badge">{selectedTenant}</span>
            <span className="surface-badge">{liveMode ? "Live mode" : "Fixture mode"}</span>
          </div>
          <p className="session-note">
            {hasSessionToken ? "ID token held in sessionStorage." : "Preview-only session."}
          </p>
        </div>
      </section>

      {authError ? (
        <section className="auth-callout" aria-live="polite">
          <strong>Hosted sign-in did not complete.</strong>
          <p>{authError}</p>
        </section>
      ) : null}

      <div className="explorer-grid">
        <aside className="flight-list-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">List</p>
              <h2>{listTitle}</h2>
            </div>
            <span className="count-pill">
              {flights.length === 1 ? "1 flight" : `${flights.length} flights`}
            </span>
          </div>

          <div className="flight-list-legend" aria-hidden="true">
            <span>trace_id</span>
            <span>status</span>
            <span>$</span>
            <span>masked</span>
          </div>

          {listFailure ? (
            <div className="empty-state">
              <strong>{listFailureCopy.title}</strong>
              <p>{listFailureCopy.copy}</p>
            </div>
          ) : flights.length > 0 ? (
            <div className="flight-list">
              {flights.map((flight) => {
                const flightSummary = summarizeFlightItem(flight);
                const isActive = selectedTraceId === flightSummary.traceId;

                return (
                  <button
                    className={`flight-row ${isActive ? "is-active" : ""}`}
                    key={flightSummary.traceId}
                    onClick={() => onSelectTrace(flightSummary.traceId)}
                    type="button"
                  >
                    <div className="flight-row__trace">
                      <strong>{flightSummary.traceId}</strong>
                      <span>{formatTimestamp(flightSummary.startTime)}</span>
                    </div>
                    <span className={`status-pill status-pill--${flightSummary.status}`}>
                      {flightSummary.status}
                    </span>
                    <span className="flight-row__cost">
                      {formatCurrency(flightSummary.costUsd)}
                    </span>
                    <div className="flight-row__preview">
                      <span className="inline-redacted">REDACTED</span>
                      <span>{flightSummary.promptPreview}</span>
                    </div>
                  </button>
                );
              })}
            </div>
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
              <div className="flight-row__trace">
                <strong>{fixtureForbiddenTraceId}</strong>
                <span>Isolation proof</span>
              </div>
              <span className="status-pill status-pill--forbidden">403</span>
              <span className="flight-row__cost">—</span>
              <div className="flight-row__preview">
                <span className="inline-redacted">REDACTED</span>
                <span>Locked tenant-b example: same trace story, denied across tenants.</span>
              </div>
            </button>
          ) : null}
        </aside>

        <section className="detail-panel">
          <div className="detail-heading">
            <div>
              <p className="eyebrow">Selected flight</p>
              <div className="detail-heading__row">
                <span className="trace-chip">trace_id={selectedTraceDisplay}</span>
                {summary ? (
                  <span className={`status-pill status-pill--${summary.status}`}>{summary.status}</span>
                ) : null}
              </div>
            </div>

            {summary ? (
              <div className="summary-line" aria-label="Flight summary">
                <div className="summary-metric">
                  <span>started</span>
                  <strong>{formatTimestamp(summary.startTime)}</strong>
                </div>
                <div className="summary-metric">
                  <span>latency</span>
                  <strong>{formatDuration(summary.durationMs)}</strong>
                </div>
                <div className="summary-metric">
                  <span>model</span>
                  <strong>{modelName}</strong>
                </div>
                <div className="summary-metric">
                  <span>tokens</span>
                  <strong>{tokenCount}</strong>
                </div>
                <div className="summary-metric">
                  <span>$</span>
                  <strong>{formatCurrency(summary.costUsd)}</strong>
                </div>
                <div className="summary-metric">
                  <span>ttl</span>
                  <strong>{selectedDetail ? formatTtl(selectedDetail.expires_at) : "7 day retention"}</strong>
                </div>
              </div>
            ) : null}
          </div>

          {isForbiddenState ? (
            <section className="forbidden-panel">
              <p className="eyebrow eyebrow--danger">{liveMode ? "Live 403" : "Contracted 403"}</p>
              <div className="forbidden-panel__hero">
                <strong>403</strong>
                <h3>{detailFailure?.code ?? forbidden.expected_body.error.code}</h3>
              </div>
              <p className="forbidden-copy">
                {liveMode && detailFailure
                  ? detailFailure.message
                  : forbidden.expected_body.error.message}
              </p>
              <dl className="forbidden-grid">
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
              <strong>Loading selected flight.</strong>
              <p>Reconstructing list, detail, and audit against the read contract.</p>
            </section>
          ) : detailStatus === "error" ? (
            <section className="empty-state">
              <strong>{detailFailureCopy.title}</strong>
              <p>{detailFailureCopy.copy}</p>
            </section>
          ) : !selectedDetail || !summary ? (
            <section className="empty-state">
              <strong>No flight selected yet.</strong>
              <p>Choose a flight from the list to reconstruct one request.</p>
            </section>
          ) : (
            <div className="detail-grid">
              <div className="detail-main">
                <section className="waterfall-panel">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">Waterfall</p>
                      <h3>Timeline reconstruction</h3>
                    </div>
                  </div>

                  <div className="timeline-axis" aria-hidden="true">
                    {[0, 0.25, 0.5, 0.75, 1].map((stop) => (
                      <span key={stop} style={{ left: `${stop * 100}%` }}>
                        {Math.round(totalTimelineMs * stop)} ms
                      </span>
                    ))}
                  </div>

                  <div className="waterfall-table">
                    {detailSpans.map((span) => {
                      const depth = depths.get(span.span_id) ?? 0;
                      const startMs = new Date(span.start_time).getTime();
                      const leftPct = ((startMs - rootStartMs) / totalTimelineMs) * 100;
                      const widthPct = Math.max((span.durationMs / totalTimelineMs) * 100, 4);
                      const tokenLabel =
                        (span["gen_ai.usage.input_tokens"] ?? 0) +
                        (span["gen_ai.usage.output_tokens"] ?? 0);
                      const errorMessage =
                        span.status === "error" ? getSpanErrorMessage(span) ?? "Span failed." : null;

                      return (
                        <article
                          className={`waterfall-row ${span.status === "error" ? "is-error" : ""}`}
                          key={span.span_id}
                        >
                          <div
                            className="waterfall-row__identity"
                            style={{ paddingInlineStart: `${depth * 18}px` }}
                          >
                            <div className="waterfall-row__name">
                              <KindBadge kind={span.kind} />
                              <strong>{span.name}</strong>
                            </div>
                            <p className="waterfall-row__meta">
                              <span>Status {span.status}</span>
                              {span["gen_ai.request.model"] ? (
                                <span>{span["gen_ai.request.model"]}</span>
                              ) : null}
                            </p>
                            {errorMessage ? (
                              <p className="waterfall-row__error">{errorMessage}</p>
                            ) : null}
                          </div>

                          <div className="waterfall-row__timeline">
                            <div className="timeline-track" aria-hidden="true">
                              <span
                                className={`timeline-bar timeline-bar--${span.kind}`}
                                style={{
                                  left: `${Math.max(leftPct, 0)}%`,
                                  width: `${Math.min(widthPct, 100)}%`,
                                }}
                              />
                            </div>
                          </div>

                          <div className="waterfall-row__metrics">
                            <span>{formatDuration(span.durationMs)}</span>
                            <span>{tokenLabel > 0 ? `${tokenLabel} tok` : "—"}</span>
                            <span>{span.cost_usd > 0 ? formatCurrency(span.cost_usd) : "—"}</span>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </section>

                <section className="rag-panel">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">RAG hops</p>
                      <h3>Masked query, doc ids, score</h3>
                    </div>
                  </div>

                  {ragHops.length > 0 ? (
                    <div className="rag-shell">
                      <div className="rag-query">
                        <span className="inline-redacted">REDACTED</span>
                        <div>
                          <strong>Prompt stored masked</strong>
                          <p>{ragHops[0]?.maskedQuery ?? firstPromptPreview}</p>
                        </div>
                      </div>

                      <div className="rag-table" role="table" aria-label="RAG hops">
                        <div className="rag-table__header" role="row">
                          <span role="columnheader">doc_id</span>
                          <span role="columnheader">score</span>
                          <span role="columnheader">top_k</span>
                        </div>
                        {ragHops.map((hop) => (
                          <div className="rag-table__row" key={hop.spanId} role="row">
                            <span role="cell">{hop.documentIds.join(", ") || "—"}</span>
                            <span role="cell">{hop.scores.join(", ") || "—"}</span>
                            <span role="cell">{hop.topK ?? "—"}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="empty-state compact-state">
                      <strong>No RAG hops captured.</strong>
                      <p>This selected flight does not include retrieval steps.</p>
                    </div>
                  )}
                </section>
              </div>

              <aside className="detail-aside">
                <section className="governance-panel">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">Governance</p>
                      <h3>REDACTED proof</h3>
                    </div>
                  </div>

                  <div className="governance-hero">
                    <span className="inline-redacted inline-redacted--hero">REDACTED</span>
                    <p>{firstPromptPreview}</p>
                  </div>

                  <dl className="governance-grid">
                    <div>
                      <dt>prompt_hash</dt>
                      <dd>{firstPromptHash ?? "No prompt hash stored."}</dd>
                    </div>
                    <div>
                      <dt>model</dt>
                      <dd>{modelName}</dd>
                    </div>
                    <div>
                      <dt>tokens</dt>
                      <dd>{tokenCount}</dd>
                    </div>
                    <div>
                      <dt>$</dt>
                      <dd>{formatCurrency(summary.costUsd)}</dd>
                    </div>
                    <div>
                      <dt>retention</dt>
                      <dd>{selectedDetail ? formatTtl(selectedDetail.expires_at) : "7 day retention"}</dd>
                    </div>
                  </dl>
                </section>

                <section className="audit-panel">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">Audit</p>
                      <h3>Who opened this flight</h3>
                    </div>
                  </div>

                  <div className="audit-band">
                    <span>TTL 7d</span>
                    <span>{liveMode ? liveAuditCopy : "Fixture mode shows the audit shape without inventing events."}</span>
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
                                <dt>tenant</dt>
                                <dd>{event.tenant_id}</dd>
                              </div>
                              <div>
                                <dt>trace_id</dt>
                                <dd>{event.trace_id}</dd>
                              </div>
                            </dl>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <div className="audit-skeleton">
                        <div className="audit-skeleton__line" />
                        <div className="audit-skeleton__row">
                          <span>actor</span>
                          <span>when</span>
                          <span>trace_id</span>
                        </div>
                        <p>The live route writes and returns the audit row here.</p>
                      </div>
                    )
                  ) : (
                    <div className="audit-skeleton">
                      <div className="audit-skeleton__line" />
                      <div className="audit-skeleton__row">
                        <span>actor</span>
                        <span>when</span>
                        <span>trace_id</span>
                      </div>
                      <p>Day 2 live GET writes the tenant-scoped audit row here.</p>
                    </div>
                  )}
                </section>
              </aside>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function KindBadge({ kind }: { kind: TraceSpan["kind"] }) {
  return <span className={`kind-badge kind-badge--${kind}`}>{kind}</span>;
}

export function ExplorerShell({ fixtures }: ExplorerShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isClientReady, setIsClientReady] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<TenantId>("tenant-a");
  const [idToken, setIdToken] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [liveFlights, setLiveFlights] = useState<FlightListItem[]>([]);
  const [listFailure, setListFailure] = useState<RequestFailure | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<FlightDetail | null>(null);
  const [detailStatus, setDetailStatus] = useState<DetailStatus>("idle");
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
    let cancelled = false;

    async function hydrateSession() {
      let token: string | null = null;

      try {
        await completeHostedUiSignIn();
        token = readStoredIdToken();
      } catch {
        token = readStoredIdToken();
        if (!cancelled) {
          setAuthError(
            "Hosted sign-in returned, but TraceVault could not complete the token exchange.",
          );
        }
      }

      if (cancelled) {
        return;
      }

      setIdToken(token);
      const storedTenant = window.sessionStorage.getItem(TENANT_STORAGE_KEY);
      const storedIdentity = readIdTokenIdentity(token);

      if (storedIdentity.tenantId) {
        setSelectedTenant(storedIdentity.tenantId);
        window.sessionStorage.setItem(TENANT_STORAGE_KEY, storedIdentity.tenantId);
      } else if (storedTenant === "tenant-a" || storedTenant === "tenant-b") {
        setSelectedTenant(storedTenant);
      }

      setIsClientReady(true);
    }

    void hydrateSession();

    return () => {
      cancelled = true;
    };
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

    if (defaultTraceId && (!selectedTraceId || (!liveMode && !fixtureTraceStillValid))) {
      const next = new URLSearchParams(searchParams.toString());
      next.set("trace_id", defaultTraceId);
      startTransition(() => {
        router.replace(`${pathname || EXPLORER_PATH}?${next.toString()}`);
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
      router.replace(`${pathname || EXPLORER_PATH}?${next.toString()}`);
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
      authError={authError}
      detailFailure={detailFailure}
      detailStatus={detailStatus}
      fixtureForbiddenTraceId={fixtureForbiddenTraceId}
      flights={activeFlights}
      fixtures={fixtures}
      listFailure={listFailure}
      liveMode={liveMode}
      onSelectTrace={setTrace}
      onSelectTenant={handleTenantChange}
      selectedDetail={selectedDetail}
      selectedSummary={selectedSummary}
      selectedTenant={selectedTenant}
      selectedTraceId={selectedTraceId}
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
      authError={null}
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
      selectedTenant={selectedTenant}
      selectedTraceId={selectedTraceId}
      signedInTenant={null}
      switcherDisabled={false}
    />
  );
}
