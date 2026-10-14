import { expect, test } from "@playwright/test";

test("record, inspect, edit and delete a trade with saved analytics", async ({
  page,
}, info) => {
  await page.goto("/journal");
  await expect(
    page.getByRole("heading", { name: "Trading Journal." }),
  ).toBeVisible();
  await expect(page.getByText("No records match this view.")).toBeVisible();
  await page.getByRole("button", { name: "Record trade", exact: true }).click();
  const form = page.getByRole("dialog");
  await form.getByLabel("Exchange", { exact: true }).fill("Browser test");
  await form
    .getByLabel("Entry time (UTC)", { exact: true })
    .fill("2025-01-01T12:00");
  await form.getByLabel("Entry price", { exact: true }).fill("100");
  await form.getByLabel("Original quantity", { exact: true }).fill("2");
  await form.getByLabel("Initial stop loss (optional)").fill("90");
  await form.getByLabel("Entry fees paid").fill("1");
  await form.getByLabel("Strategy / setup tag").fill("Patient breakout");
  await form
    .getByLabel("Rationale & notes")
    .fill("Disposable browser test record");
  await form.getByRole("button", { name: "Add exit" }).click();
  await form
    .getByLabel("Exit time (UTC)", { exact: true })
    .fill("2025-01-02T12:00");
  await form.getByLabel("Exit price", { exact: true }).fill("110");
  await form.getByLabel("Exit quantity", { exact: true }).fill("2");
  await form.getByLabel("Exit fees", { exact: true }).fill("1");
  await form.getByRole("button", { name: "Save trade", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page
      .locator(".journal-stat-grid")
      .getByText("$18.00", { exact: true })
      .first(),
  ).toBeVisible();
  await expect(page.getByText("Patient breakout · spot · buy")).toBeVisible();
  await expect(page.locator(".recharts-surface").first()).toBeVisible();
  await page.screenshot({
    path: info.outputPath("journal-recorded.png"),
    fullPage: true,
    caret: "initial",
  });
  await page.getByRole("button", { name: "View BTC/USD trade" }).click();
  await expect(
    page.getByRole("dialog").getByText("0.90R", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit trade", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByLabel("Rationale & notes")
    .fill("Updated browser reflection");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page
    .getByRole("textbox", { name: "Search journal" })
    .fill("Updated browser reflection");
  await expect(
    page.getByText("1 matching records", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "View BTC/USD trade" }).click();
  await expect(
    page.getByRole("dialog").getByText("Updated browser reflection"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Delete trade", exact: true }).click();
  await page
    .getByRole("button", { name: "Confirm delete", exact: true })
    .click();
  await expect(page.getByText("No records match this view.")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});

test("invalid entry gets friendly form feedback", async ({ page }) => {
  await page.goto("/journal");
  await page.getByRole("button", { name: "Record trade", exact: true }).click();
  await page.getByRole("button", { name: "Save trade", exact: true }).click();
  await expect(page.getByText("Enter the exchange.")).toBeVisible();
  await expect(page.getByRole("dialog")).toBeVisible();
});
