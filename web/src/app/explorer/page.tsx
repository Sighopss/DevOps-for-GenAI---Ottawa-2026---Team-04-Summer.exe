import { Suspense } from "react";
import { ExplorerShell, ExplorerShellFallback } from "@/components/explorer-shell";
import { loadFixtureFlight, loadForbiddenFixture } from "@/lib/fixture";
import { summarizeFlight } from "@/lib/flight";

export default function ExplorerPage() {
  const flight = loadFixtureFlight();
  const forbidden = loadForbiddenFixture();
  const summary = summarizeFlight(flight.spans);

  return (
    <Suspense
      fallback={
        <ExplorerShellFallback
          flight={flight}
          forbidden={forbidden}
          summary={summary}
        />
      }
    >
      <ExplorerShell flight={flight} forbidden={forbidden} summary={summary} />
    </Suspense>
  );
}
