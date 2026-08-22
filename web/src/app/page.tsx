"use client";

import Link from "next/link";
import { useEffect } from "react";
import {
  buildHostedUiUrl,
  hasHostedUiConfig,
  persistIdTokenFromHash,
} from "@/lib/cognito";

function TraceVaultMark() {
  return (
    <div className="tv-mark" aria-label="TraceVault">
      <span className="tv-mark__vault">TRACEVAULT</span>
      <span className="tv-mark__sub">Unified AI observability with fail-closed storage.</span>
    </div>
  );
}

export default function WelcomePage() {
  const hostedUiEnabled = hasHostedUiConfig();

  useEffect(() => {
    persistIdTokenFromHash();
  }, []);

  const handleSignIn = () => {
    if (!hostedUiEnabled || typeof window === "undefined") {
      return;
    }

    window.location.assign(buildHostedUiUrl(`${window.location.origin}/explorer`));
  };

  return (
    <main className="welcome-shell">
      <section className="welcome-panel">
        <p className="eyebrow">Explorer / Welcome</p>
        <TraceVaultMark />
        <h1>Replay one AI request without turning observability into a leak path.</h1>
        <p className="lede">
          TraceVault reconstructs one flight at a time: spans, RAG hops, token usage,
          cost, and redaction state for an on-call operator who needs the truth fast.
        </p>
        <p className="limitation">
          Prompts are stored masked, never raw, and traces expire after seven days.
        </p>
        <div className="cta-row">
          {hostedUiEnabled ? (
            <button className="primary-cta" onClick={handleSignIn} type="button">
              Sign in with Cognito
            </button>
          ) : (
            <button className="primary-cta is-disabled" disabled type="button">
              Sign in with Cognito
            </button>
          )}
          <Link className="secondary-cta" href="/explorer">
            Open Day 1 fixture
          </Link>
        </div>
        {!hostedUiEnabled ? (
          <p className="helper-copy">
            Set Trevor&apos;s `NEXT_PUBLIC_COGNITO_*` values to enable hosted sign-in.
          </p>
        ) : null}
      </section>
    </main>
  );
}
