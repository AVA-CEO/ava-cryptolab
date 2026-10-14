import { expect, test } from "@playwright/test";

test("empty workspace, explicit sample mode and date filters", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Command Center." }),
  ).toBeVisible();
  await expect(
    page.getByText("Your story starts with one trade."),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("empty-workspace.png"),
    fullPage: true,
    caret: "initial",
  });
  await page.getByRole("button", { name: "Explore sample data" }).click();
  await expect(
    page.getByText("SIMULATED DATA · Educational examples only"),
  ).toBeVisible();
  await expect(page.locator(".recharts-surface").first()).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("sample-workspace.png"),
    fullPage: true,
    caret: "initial",
  });
  await page.getByRole("button", { name: "7D", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "7D", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByText("Last 7 sample days", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Daily PnL", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Daily PnL", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Exit sample mode" }).click();
  await expect(
    page.getByText("Your story starts with one trade."),
  ).toBeVisible();
});

test("theme, route previews and responsive layout", async ({
  page,
  isMobile,
}, testInfo) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Toggle color theme" }).click();
  await expect(page.locator("html")).toHaveClass(/light/);
  await page.reload();
  await expect(page.locator("html")).toHaveClass(/light/);
  await page.screenshot({
    path: testInfo.outputPath("light-workspace.png"),
    fullPage: true,
    caret: "initial",
  });
  if (isMobile) {
    await page.getByRole("button", { name: "Open navigation" }).click();
    await page.keyboard.press("Escape");
    await expect(
      page.getByRole("button", { name: "Open navigation" }),
    ).toBeFocused();
    await page.getByRole("button", { name: "Open navigation" }).click();
  }
  await page
    .getByRole("link", { name: "Trading Journal", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Trading Journal.", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("LOCAL PRIVATE JOURNAL")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("workspace controls and unknown routes", async ({ page, isMobile }) => {
  await page.goto("/");
  if (!isMobile) {
    await page.getByRole("button", { name: "Collapse sidebar" }).click();
    await expect(page.locator(".app-shell")).toHaveClass(/is-collapsed/);
    await page.getByRole("button", { name: "Expand sidebar" }).click();
    await page
      .getByRole("textbox", { name: "Search workspace" })
      .fill("Academy");
    await expect(
      page
        .locator(".search-results")
        .getByRole("link", { name: "Crypto Academy" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Clear search" }).click();
  }
  await page.getByRole("button", { name: "Notifications" }).click();
  await expect(page.getByText("You’re all caught up")).toBeVisible();
  await page.goto("/unknown-module");
  await expect(
    page.getByRole("heading", { name: "Page not found" }),
  ).toBeVisible();
});
