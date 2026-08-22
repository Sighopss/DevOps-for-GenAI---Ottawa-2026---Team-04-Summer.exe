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

test("fixture A renders the explorer flow", async ({ page }) => {
  await page.goto("/explorer");

  await expect(
    page.getByRole("heading", { name: "One flight. No raw prompt storage." }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Signed-in list" })).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Parent-child, latency, tokens, and cost",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Masked query, document IDs, and scores",
    }),
  ).toBeVisible();
  await expect(page.getByText("REDACTED")).toBeVisible();
  await expect(page.getByText("Day 1 fixture only")).toBeVisible();
});

test("fixture screens show masked placeholders instead of raw SSN or email", async ({
  page,
}) => {
  await page.goto("/explorer");
  await page.getByLabel("Tenant").selectOption("tenant-b");
  await expect(page.getByLabel("Tenant")).toHaveValue("tenant-b");

  const text = await page.locator("body").innerText();

  expect(text).toContain("[EMAIL]");
  expect(text).toContain("[SSN]");
  expect(text).not.toMatch(/\b\d{3}-\d{2}-\d{4}\b/);
  expect(text).not.toMatch(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
  await expect(page.getByText("Locked contract example:", { exact: false })).toBeVisible();
});

test("live tenant-b sees 403 chrome from the read API, not a blank detail view", async ({
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

  await page.goto(`/explorer?trace_id=${traceA}`);

  await expect(page.getByText("Live read active")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "403 forbidden: tenant mismatch" }),
  ).toBeVisible();
  await expect(page.locator(".forbidden-copy")).toHaveText("forbidden: tenant mismatch");
  await expect(
    page.getByText("Live reads follow the signed-in ID token for tenant-b."),
  ).toBeVisible();

  const text = await page.locator("body").innerText();
  expect(text).not.toMatch(/\b\d{3}-\d{2}-\d{4}\b/);
});
