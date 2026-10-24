import { expect, test } from "@playwright/test";

test("forex preview uses Python, stays unsaved and rejects over-closing", async ({
  page,
}) => {
  await page.goto("/cfd-preview");
  await expect(page.getByLabel("Original lots", { exact: true })).toHaveValue(
    "0.10",
  );
  await page.getByRole("button", { name: "Calculate unsaved preview" }).click();
  await expect(page.getByText("8.00 USD").first()).toBeVisible({
    timeout: 25000,
  });
  await expect(
    page.getByText("0.06 lots remaining", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Save", exact: true }),
  ).toHaveCount(0);
  await page.getByLabel("Exit lots", { exact: true }).fill("0.11");
  await page.getByRole("button", { name: "Calculate unsaved preview" }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Check the CFD request fields" }),
  ).toContainText("Check the CFD request fields");
  await expect(
    page.getByText("Inputs changed.", { exact: false }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
});

test("academy completion persists and trivia answers are checked on server", async ({
  page,
  request,
}) => {
  await page.goto("/academy");
  await page.getByRole("button", { name: "Mark lesson complete" }).click();
  await page.reload();
  await expect(
    page.getByText("1 / 8 lessons marked complete", { exact: false }),
  ).toBeVisible();
  const catalog = await (await request.get("/api/learning")).json();
  expect(catalog.questions).toHaveLength(16);
  expect(catalog.questions[0]).not.toHaveProperty("answer");
  const forged = await request.post("/api/learning", {
    data: { question_id: "money-1", choice: 1, correct: true },
  });
  expect(forged.status()).toBe(422);
  await page.goto("/trivia");
  await page
    .getByRole("button", { name: "B · It uses network rules", exact: false })
    .click();
  await page.getByRole("button", { name: "Check answer" }).click();
  await expect(page.getByRole("status")).toContainText("Correct");
  await expect(
    page.getByText("1 correct / 1 answered", { exact: false }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("1 correct / 1 answered", { exact: false }),
  ).toBeVisible();
});

test("JPY conversions, metals and signed costs use the declared specifications", async ({
  page,
}) => {
  test.setTimeout(60000);
  await page.goto("/cfd-preview");
  const instrument = page.getByLabel("Teaching instrument");
  await expect(instrument).toHaveValue("EURUSD");
  await instrument.selectOption("USDJPY");
  await page.getByRole("button", { name: "Calculate unsaved preview" }).click();
  await expect(page.getByText("800 JPY", { exact: true }).first()).toBeVisible({
    timeout: 25000,
  });
  await page.getByLabel("Signed commission", { exact: false }).fill("-100");
  await page.getByLabel("Hypothetical USD per 1 JPY (optional)").fill("0.005");
  await page.getByRole("button", { name: "Calculate unsaved preview" }).click();
  await expect(page.getByText("3.50 USD", { exact: true })).toBeVisible({
    timeout: 25000,
  });
  for (const [symbol, expected] of [
    ["XAUUSD", "8.00 USD"],
    ["XAGUSD", "4.00 USD"],
  ]) {
    await instrument.selectOption(symbol);
    await page
      .getByRole("button", { name: "Calculate unsaved preview" })
      .click();
    await expect(page.getByText(expected, { exact: true }).first()).toBeVisible(
      { timeout: 25000 },
    );
  }
});

test("candle lab explains interval direction without predicting prices", async ({
  page,
}) => {
  await page.goto("/lab");
  await page.getByRole("button", { name: "bullish", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Correct");
  await page.getByRole("button", { name: "Next candle" }).click();
  await page.getByRole("button", { name: "bearish", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Close is below open");
});

test("educational market watchlist persists without live-data claims", async ({
  page,
}) => {
  await page.goto("/markets");
  await expect(
    page.getByText("All figures below are fictional", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Watch BTC", exact: true }).click();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Watch BTC", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "My browser watchlist (1)" }).click();
  await expect(
    page.getByRole("button", { name: "Watch ETH", exact: true }),
  ).toHaveCount(0);
  await page.getByLabel("Find an asset", { exact: false }).fill("nomatch");
  await expect(
    page.getByText("No matching examples.", { exact: false }),
  ).toBeVisible();
});

test("Trading IQ preserves currency isolation and empty evidence state", async ({
  page,
}) => {
  await page.goto("/insights");
  await page.getByLabel("Settlement currency").selectOption("USDC");
  await expect(
    page.getByText("No fully closed trades", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText("Minimum 20 overall", { exact: false }),
  ).toBeVisible();
});
