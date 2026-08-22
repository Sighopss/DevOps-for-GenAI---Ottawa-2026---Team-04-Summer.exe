"use client";

import Image from "next/image";
import Link from "next/link";
import { buildHostedUiUrl, hasHostedUiConfig } from "@/lib/cognito";

const EXPLORER_PATH = "/explorer/";

function TraceVaultMark() {
  return (
    <Image
      alt="TraceVault enterprise mark"
      className="brand-mark brand-mark--hero"
      height={4608}
      src="/tracevault-enterprise.png"
      unoptimized
      width={3072}
    />
  );
}

export default function WelcomePage() {
  const hostedUiEnabled = hasHostedUiConfig();

  const handleSignIn = async () => {
    if (!hostedUiEnabled || typeof window === "undefined") {
      return;
    }

    const redirectUri = `${window.location.origin}${EXPLORER_PATH}`;
    window.location.assign(await buildHostedUiUrl(redirectUri));
  };

  return (
    <main className="welcome-shell">
      <section className="welcome-panel">
        <p className="eyebrow">Fail-closed ops gate</p>
        <TraceVaultMark />
        <p className="welcome-purpose">
          Replay one flight fast: latency, RAG hops, spend, and tenant isolation on one
          operator screen.
        </p>
        <p className="welcome-limitation">
          Prompt stored masked. Cross-tenant reads fail closed. Traces expire after
          seven days.
        </p>
        <div className="cta-row">
          {hostedUiEnabled ? (
            <button
              className="primary-cta"
              onClick={() => {
                void handleSignIn();
              }}
              type="button"
            >
              Sign in with Cognito
            </button>
          ) : (
            <button className="primary-cta is-disabled" disabled type="button">
              Hosted sign-in offline
            </button>
          )}
          <Link className="secondary-cta" href={EXPLORER_PATH}>
            Preview sample flight
          </Link>
        </div>
        {!hostedUiEnabled ? (
          <p className="helper-copy">Hosted sign-in is unavailable in this build.</p>
        ) : null}
      </section>
    </main>
  );
}
