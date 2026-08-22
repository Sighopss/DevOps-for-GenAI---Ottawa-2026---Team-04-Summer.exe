import { expect, test } from "@playwright/test";

function buildIdToken(tenant: "tenant-a" | "tenant-b"): string {
  const encode = (value: object) =>
    Buffer.from(JSON.stringify(value)).toString("base64url");

  return [
    encode({ alg: "none", typ: "JWT" }),
    encode({
      "custom:tenant_id": tenant,
      "cognito:username": tenant,
      sub: `${tenant}-sub`,
    }),
    "signature",
  ].join(".");
}

function expectMaskedPlaceholders(text: string) {
  expect(text).toContain("[EMAIL]");
  expect(text).toContain("[SSN]");
}

function expectNoRawPii(text: string) {
  expect(text).not.toMatch(/\b\d{3}-\d{2}-\d{4}\b/);
  expect(text).not.toMatch(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
}

test("hosted UI code callback exchanges tokens and forwards into the explorer", async ({
  page,
}) => {
  const traceA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
  const state = "state-token";
  const codeVerifier = "verifier-token";

  await page.addInitScript(
    ({ storedState, storedVerifier }) => {
      window.sessionStorage.setItem("tracevault.oauth_state", storedState);
      window.sessionStorage.setItem("tracevault.code_verifier", storedVerifier);
    },
    { storedState: state, storedVerifier: codeVerifier },
  );

  await page.route(
    "https://tracevault.auth.us-east-1.amazoncognito.com/oauth2/token",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id_token: buildIdToken("tenant-a"),
          access_token: "access-token",
          refresh_token: "refresh-token",
          token_type: "Bearer",
          expires_in: 3600,
        }),
      });
    },
  );

  await page.route("http://127.0.0.1:4010/v1/traces?limit=50", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        flights: [
          {
            trace_id: traceA,
            tenant_id: "tenant-a",
            start_time: "2026-08-18T18:00:00.000Z",
            end_time: "2026-08-18T18:00:01.200Z",
            cost_usd: 0.0021,
            status: "ok",
            prompt_preview: "User [EMAIL] asked about [SSN]",
          },
        ],
      }),
    });
  });

  await page.route(`http://127.0.0.1:4010/v1/traces/${traceA}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        trace_id: traceA,
        tenant_id: "tenant-a",
        expires_at: 1787421600,
        spans: [
          {
            trace_id: traceA,
            span_id: "1111111111111111",
            parent_id: null,
            tenant_id: "tenant-a",
            kind: "http",
            name: "demo.ask",
            status: "ok",
            start_time: "2026-08-18T18:00:00.000Z",
            end_time: "2026-08-18T18:00:01.200Z",
            cost_usd: 0,
            attributes: { route: "/ask" },
          },
        ],
      }),
    });
  });

  await page.route(`http://127.0.0.1:4010/v1/traces/${traceA}/audit`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        events: [],
      }),
    });
  });

  await page.goto(`/explorer/?code=auth-code&state=${state}`);

  await page.waitForURL("**/explorer/**");
  await expect(page.getByText("Live mode")).toBeVisible();
  await expect(
    page.getByText("Signed in as tenant-a. Reads stay tenant-scoped through the ID token."),
  ).toBeVisible();
  await expect(await page.evaluate(() => window.sessionStorage.getItem("tracevault.id_token"))).toBeTruthy();
});

test("fixture A renders the explorer flow", async ({ page }) => {
  const consoleMessages: string[] = [];
  page.on("console", (message) => {
    consoleMessages.push(message.text());
  });

  await page.goto("/explorer/");

  await expect(
    page.getByRole("heading", { name: "Fixture flights" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Timeline reconstruction",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Masked query, doc ids, score",
    }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "REDACTED proof" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Who opened this flight" })).toBeVisible();
  await expect(page.locator(".surface-badge").filter({ hasText: "REDACTED" })).toBeVisible();
  await expect(page.getByText("Committed fixture replay")).toBeVisible();

  const text = await page.locator("body").innerText();
  expectMaskedPlaceholders(text);
  expectNoRawPii(text);
  expect(consoleMessages.join("\n")).not.toContain("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
  expect(consoleMessages.join("\n")).not.toContain("User [EMAIL] asked about [SSN]");
});

test("fixture tenant-b keeps Day 1 honest and shows only the locked 403 contract example", async ({
  page,
}) => {
  await page.goto("/explorer/");
  await page.getByLabel("Tenant").selectOption("tenant-b");
  await expect(page.getByLabel("Tenant")).toHaveValue("tenant-b");

  await expect(page.getByText("No flights to display.")).toBeVisible();
  await expect(
    page.getByText("Tenant-b only gets the locked 403 contract example on Day 1.", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", {
      name: /Isolation proof/,
    }),
  ).toBeVisible();
  await expect(page.getByText("Contracted 403")).toBeVisible();

  const text = await page.locator("body").innerText();
  expectNoRawPii(text);
  expect(await page.evaluate(() => Object.keys(window.localStorage))).toEqual([]);
});

test("live detail makes failures, latency, model, cost, and audit legible", async ({
  page,
}) => {
  const traceA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

  await page.addInitScript((token) => {
    window.sessionStorage.setItem("tracevault.id_token", token);
    window.sessionStorage.setItem("tracevault.tenant", "tenant-a");
  }, buildIdToken("tenant-a"));

  await page.route("http://127.0.0.1:4010/v1/traces?limit=50", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        flights: [
          {
            trace_id: traceA,
            tenant_id: "tenant-a",
            start_time: "2026-08-18T18:00:00.000Z",
            end_time: "2026-08-18T18:00:01.200Z",
            cost_usd: 0.0021,
            status: "error",
            prompt_preview: "User [EMAIL] asked about [SSN]",
          },
        ],
      }),
    });
  });

  await page.route(`http://127.0.0.1:4010/v1/traces/${traceA}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        trace_id: traceA,
        tenant_id: "tenant-a",
        expires_at: 1787421600,
        spans: [
          {
            trace_id: traceA,
            span_id: "1111111111111111",
            parent_id: null,
            tenant_id: "tenant-a",
            kind: "http",
            name: "demo.ask",
            status: "error",
            start_time: "2026-08-18T18:00:00.000Z",
            end_time: "2026-08-18T18:00:01.200Z",
            cost_usd: 0,
            attributes: { route: "/ask", error_message: "downstream llm failed" },
          },
          {
            trace_id: traceA,
            span_id: "aaaa111111111111",
            parent_id: "1111111111111111",
            tenant_id: "tenant-a",
            kind: "rag",
            name: "demo.retrieve",
            status: "ok",
            start_time: "2026-08-18T18:00:00.050Z",
            end_time: "2026-08-18T18:00:00.280Z",
            cost_usd: 0,
            prompt_preview: "User [EMAIL] asked about [SSN]",
            attributes: {
              "rag.document_ids": ["doc-policy-01"],
              "rag.scores": [0.98],
              "rag.top_k": 1,
            },
          },
          {
            trace_id: traceA,
            span_id: "cccc333333333333",
            parent_id: "1111111111111111",
            tenant_id: "tenant-a",
            kind: "llm",
            name: "demo.converse",
            status: "error",
            start_time: "2026-08-18T18:00:00.370Z",
            end_time: "2026-08-18T18:00:01.150Z",
            cost_usd: 0.0021,
            prompt_preview: "User [EMAIL] asked about [SSN]",
            "gen_ai.request.model": "anthropic.claude-sonnet-4-20250514-v1:0",
            "gen_ai.usage.input_tokens": 120,
            "gen_ai.usage.output_tokens": 40,
            attributes: { error_message: "Bedrock timed out" },
          },
        ],
      }),
    });
  });

  await page.route(`http://127.0.0.1:4010/v1/traces/${traceA}/audit`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        events: [
          {
            actor: "tenant-a",
            tenant_id: "tenant-a",
            trace_id: traceA,
            ts: "2026-08-18T18:02:00.000Z",
          },
        ],
      }),
    });
  });

  await page.goto(`/explorer/?trace_id=${traceA}`);

  await expect(page.getByText("Live mode")).toBeVisible();
  await expect(page.locator(".summary-line")).toContainText(
    "anthropic.claude-sonnet-4-20250514-v1:0",
  );
  await expect(page.getByText("Bedrock timed out")).toBeVisible();
  await expect(page.locator(".waterfall-row.is-error")).toHaveCount(2);
  await expect(page.getByText("REDACTED proof")).toBeVisible();
  await expect(page.locator(".governance-grid")).toContainText("prompt_hash");
  await expect(page.locator(".audit-row")).toContainText("tenant-a");
  await expect(page.getByText("doc-policy-01")).toBeVisible();

  const text = await page.locator("body").innerText();
  expectMaskedPlaceholders(text);
  expectNoRawPii(text);
});

test("live tenant-b sees 403 chrome from the read API and never sees tenant-a rows", async ({
  page,
}) => {
  const traceA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
  const traceB = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

  await page.addInitScript((token) => {
    window.sessionStorage.setItem("tracevault.id_token", token);
    window.sessionStorage.setItem("tracevault.tenant", "tenant-b");
  }, buildIdToken("tenant-b"));

  await page.route("http://127.0.0.1:4010/v1/traces?limit=50", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        flights: [
          {
            trace_id: traceB,
            tenant_id: "tenant-b",
            start_time: "2026-08-18T18:01:00.000Z",
            end_time: "2026-08-18T18:01:00.900Z",
            cost_usd: 0.0021,
            status: "ok",
            prompt_preview: "User [EMAIL] asked about [SSN]",
          },
        ],
      }),
    });
  });

  await page.route(`http://127.0.0.1:4010/v1/traces/${traceA}`, async (route) => {
    await route.fulfill({
      status: 403,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "forbidden",
          message: "tenant mismatch",
        },
      }),
    });
  });

  await page.goto(`/explorer/?trace_id=${traceA}`);

  await expect(page.getByText("Live mode")).toBeVisible();
  await expect(page.getByText("Live 403")).toBeVisible();
  await expect(page.getByRole("heading", { name: "forbidden" })).toBeVisible();
  await expect(page.locator(".forbidden-copy")).toHaveText("tenant mismatch");
  await expect(
    page.getByText("Signed in as tenant-b. Reads stay tenant-scoped through the ID token."),
  ).toBeVisible();
  await expect(page.locator(".flight-list-panel")).toContainText(traceB);
  await expect(page.locator(".flight-list-panel")).not.toContainText(traceA);

  const text = await page.locator("body").innerText();
  expectMaskedPlaceholders(text);
  expectNoRawPii(text);
  expect(await page.evaluate(() => Object.keys(window.localStorage))).toEqual([]);
  expect(await page.evaluate(() => window.sessionStorage.getItem("tracevault.id_token"))).toBeTruthy();
});

test("live detail shows trace-not-found from the contracted error body", async ({ page }) => {
  const traceA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

  await page.addInitScript((token) => {
    window.sessionStorage.setItem("tracevault.id_token", token);
    window.sessionStorage.setItem("tracevault.tenant", "tenant-a");
  }, buildIdToken("tenant-a"));

  await page.route("http://127.0.0.1:4010/v1/traces?limit=50", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        flights: [
          {
            trace_id: traceA,
            tenant_id: "tenant-a",
            start_time: "2026-08-18T18:00:00.000Z",
            end_time: "2026-08-18T18:00:01.200Z",
            cost_usd: 0.0021,
            status: "ok",
            prompt_preview: "User [EMAIL] asked about [SSN]",
          },
        ],
      }),
    });
  });

  await page.route(`http://127.0.0.1:4010/v1/traces/${traceA}`, async (route) => {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "not_found",
          message: "trace missing",
        },
      }),
    });
  });

  await page.goto(`/explorer/?trace_id=${traceA}`);

  await expect(page.getByText("Trace not found.")).toBeVisible();
  await expect(
    page.getByText("This trace_id was not returned for the signed-in tenant."),
  ).toBeVisible();
});

test("live list shows API unreachable when GET /v1/traces* cannot be reached", async ({
  page,
}) => {
  await page.addInitScript((token) => {
    window.sessionStorage.setItem("tracevault.id_token", token);
    window.sessionStorage.setItem("tracevault.tenant", "tenant-a");
  }, buildIdToken("tenant-a"));

  await page.route("http://127.0.0.1:4010/v1/traces?limit=50", async (route) => {
    await route.abort("failed");
  });

  await page.goto("/explorer/");

  await expect(page.getByText("API unreachable.")).toHaveCount(1);
  await expect(
    page.getByText("Could not reach GET /v1/traces*. Check the live read deployment."),
  ).toBeVisible();
});
