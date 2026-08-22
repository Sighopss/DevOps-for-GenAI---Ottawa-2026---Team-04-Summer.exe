import { expect, test } from "@playwright/test";

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
});

test("fixture screens show masked placeholders instead of raw SSN or email", async ({
  page,
}) => {
  await page.goto("/explorer");

  const text = await page.locator("body").innerText();

  expect(text).toContain("[EMAIL]");
  expect(text).toContain("[SSN]");
  expect(text).not.toMatch(/\b\d{3}-\d{2}-\d{4}\b/);
  expect(text).not.toMatch(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
});

test("tenant-b sees contracted 403 chrome, not a blank detail view", async ({
  page,
}) => {
  await page.goto("/explorer");
  await page.getByLabel("Tenant").selectOption("tenant-b");

  await expect(page.getByText("403 forbidden")).toBeVisible();
  await expect(page.getByText("tenant mismatch")).toBeVisible();
  await expect(page.getByText("No flights for tenant-b.")).toBeVisible();

  const text = await page.locator("body").innerText();
  expect(text).not.toMatch(/\b\d{3}-\d{2}-\d{4}\b/);
});
