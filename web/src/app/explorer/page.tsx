import { Suspense } from "react";
import { ExplorerShell, ExplorerShellFallback } from "@/components/explorer-shell";
import { loadFixtureData } from "@/lib/fixture";

export default function ExplorerPage() {
  const fixtures = loadFixtureData();

  return (
    <Suspense
      fallback={
        <ExplorerShellFallback fixtures={fixtures} />
      }
    >
      <ExplorerShell fixtures={fixtures} />
    </Suspense>
  );
}
