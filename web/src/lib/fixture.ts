import fs from "node:fs";
import path from "node:path";
import type { FlightFixture, ForbiddenFixture, TraceSpan } from "@/lib/types";

function withDurations(spans: Omit<TraceSpan, "durationMs">[]): TraceSpan[] {
  return spans.map((span) => {
    const start = new Date(span.start_time).getTime();
    const end = new Date(span.end_time).getTime();

    return {
      ...span,
      durationMs: Math.max(end - start, 0),
    };
  });
}

export function loadFixtureFlight(): FlightFixture {
  const fixturePath = path.join(
    process.cwd(),
    "..",
    "contracts",
    "fixtures",
    "tenant-a-rag.json",
  );
  const raw = fs.readFileSync(fixturePath, "utf-8");
  const parsed = JSON.parse(raw) as { spans: Omit<TraceSpan, "durationMs">[] };

  return {
    spans: withDurations(parsed.spans),
  };
}

export function loadForbiddenFixture(): ForbiddenFixture {
  const fixturePath = path.join(
    process.cwd(),
    "..",
    "contracts",
    "fixtures",
    "tenant-b-forbidden.json",
  );
  const raw = fs.readFileSync(fixturePath, "utf-8");

  return JSON.parse(raw) as ForbiddenFixture;
}
