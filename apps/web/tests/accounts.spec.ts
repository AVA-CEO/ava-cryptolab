import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

test("practice accounts preserve immutable instrument history", async ({
  page,
}, info) => {
  const broker = `Synthetic browser ${info.project.name}`;
  const fixture = JSON.parse(
    readFileSync(
      resolve(
        __dirname,
        "../../../services/api/tests/fixtures/cfd-input.synthetic.json",
      ),
      "utf8",
    ),
  );
  const spec = {
    ...fixture.snapshot.specification,
    broker,
    instrument_id: `synthetic-browser-${info.project.name}`,
  };
  await page.goto("/accounts");
  await expect(
    page.getByRole("heading", { name: "Trading Accounts." }),
  ).toBeVisible();
  await page
    .getByLabel("Account name", { exact: true })
    .fill(`Practice ${info.project.name}`);
  await page.getByLabel("Broker", { exact: true }).fill(broker);
  await page.getByLabel("Platform", { exact: true }).selectOption("mt5");
  await page
    .getByLabel("Server / venue (required for MT5)")
    .fill("Synthetic server");
  await page.getByLabel("Reporting currency", { exact: true }).fill("GBP");
  await page.getByLabel("Settlement currency", { exact: true }).fill("USD");
  await page
    .getByRole("button", { name: "Create practice account", exact: true })
    .click();
  await expect(
    page.getByText(
      "Practice account created. No historical trades were assigned.",
    ),
  ).toBeVisible();
  await page
    .getByLabel("Documented specification JSON")
    .fill(JSON.stringify(spec));
  await page
    .getByRole("button", { name: "Register specification", exact: true })
    .click();
  await expect(page.locator(".account-spec")).toHaveCount(1);
  spec.contract_size = "200000";
  await page
    .getByLabel("Documented specification JSON")
    .fill(JSON.stringify(spec));
  await page
    .getByRole("button", { name: "Register specification", exact: true })
    .click();
  await expect(page.locator(".account-spec")).toHaveCount(2);
  await page
    .getByRole("button", { name: "Select specification for review" })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Selected for review" }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByText("Contract size 100000 · Pip size 0.0001"),
  ).toBeVisible();
  await expect(
    page.getByText("Contract size 200000 · Pip size 0.0001"),
  ).toBeVisible();
  await page.screenshot({
    path: info.outputPath("accounts-practice-dark.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Toggle color theme" }).click();
  await page.screenshot({
    path: info.outputPath("accounts-practice-light.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.reload();
  await page
    .getByRole("button", {
      name: new RegExp(`Practice ${info.project.name} ${broker}`),
    })
    .click();
  await expect(page.locator(".account-spec")).toHaveCount(2);
  spec.broker = "Incompatible broker";
  await page
    .getByLabel("Documented specification JSON")
    .fill(JSON.stringify(spec));
  await page
    .getByRole("button", { name: "Register specification", exact: true })
    .click();
  await expect(
    page.getByRole("alert", { name: "Account management error" }),
  ).toContainText("must match");
  await expect(page.locator(".account-spec")).toHaveCount(2);
});

test("management bridge rejects foreign origins and unsupported operations", async ({
  request,
}) => {
  const response = await request.post("/api/management/accounts", {
    headers: { Origin: "https://example.com" },
    data: {},
  });
  expect(response.status()).toBe(403);
  expect(
    (await request.delete("/api/management/accounts/unknown")).status(),
  ).toBe(405);
  expect((await request.get("/api/management/secrets")).status()).toBe(404);
});
