import { expect, test } from "@playwright/test";

test("CFD position calculates, saves exact reviewed inputs and reopens after refresh", async ({
  page,
}, testInfo) => {
  test.setTimeout(120000);
  await page.goto("/cfd-journal");
  await expect(page.getByLabel("Original lots", { exact: true })).toHaveValue(
    "0.10",
  );
  await page.getByRole("button", { name: "Add exit", exact: false }).click();
  await page.getByLabel("Exit lots", { exact: true }).nth(1).fill("0.06");
  await page.getByLabel("Exit price", { exact: true }).nth(1).fill("1.10300");
  await page.getByLabel("Signed commission", { exact: false }).fill("-2");
  await page.getByLabel("Signed swap", { exact: false }).fill("-1");
  await page.getByLabel("Other signed fee", { exact: false }).fill("-1");
  const previewRequest = page.waitForRequest(
    (request) =>
      request.url().includes("/api/cfd-journal?action=preview") &&
      request.method() === "POST",
  );
  await page.getByRole("button", { name: "Calculate unsaved preview" }).click();
  const previewed = (await previewRequest).postDataJSON();
  await expect(
    page.getByText("22.00 USD", { exact: true }).first(),
  ).toBeVisible({ timeout: 30000 });
  const saveButton = page.getByRole("button", {
    name: "Save verified position",
    exact: true,
  });
  await expect(saveButton).toBeEnabled();
  const savedResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/api/cfd-journal?action=positions") &&
      response.request().method() === "POST",
  );
  await saveButton.click();
  const response = await savedResponse;
  expect(response.status()).toBe(201);
  const saved = await response.json();
  expect(response.request().postDataJSON()).toEqual(previewed);
  expect(saved.position_id).toBe(previewed.position_reference);
  expect(saved.result.remaining_lots).toBe("0");
  expect(saved.result.native.net_pnl.rounded).toBe("22");
  expect(saved.result.native.original_planned_risk.rounded).toBe("20");
  expect(saved.result.native.realized_r.rounded).toBe("1.1");
  expect(saved.provenance).toMatchObject({
    kind: "local_personal",
    input_kind: "synthetic_practice",
    accepted_calculation: true,
    broker_authenticated: false,
  });
  const detail = page.getByRole("region", {
    name: "Saved CFD trade detail",
    exact: true,
  });
  await expect(detail).toBeVisible();
  await expect(
    detail.getByText("22.00 USD", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    detail.getByText("historical replay not run", { exact: false }),
  ).toBeVisible();
  await page.reload();
  const open = page.getByRole("button", {
    name: `Open EURUSD position ${saved.position_id.slice(0, 8)}`,
    exact: true,
  });
  await expect(open).toBeVisible();
  await open.click();
  await expect(detail).toBeVisible();
  await expect(
    detail.getByText("1.100000 R", { exact: true }).first(),
  ).toBeVisible();
  await detail
    .getByText("Entry and initial exit history", { exact: true })
    .click();
  await expect(
    detail.getByText("0.06 lots at 1.103", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /delete|amend|edit saved/i }),
  ).toHaveCount(0);
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("saved-cfd-journal.png"),
    fullPage: true,
  });
});

test("lost save response retries the same receipt and does not duplicate a CFD position", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  await page.goto("/cfd-journal");
  await expect(page.getByLabel("Original lots", { exact: true })).toHaveValue(
    "0.10",
  );
  await page.getByRole("button", { name: "Calculate unsaved preview" }).click();
  const saveButton = page.getByRole("button", {
    name: "Save verified position",
    exact: true,
  });
  await expect(saveButton).toBeEnabled({ timeout: 30000 });
  const attempts: { key: string | undefined; body: string | null }[] = [];
  let savedId = "";
  let accountId = "";
  let loseResponse = true;
  await page.route("**/api/cfd-journal?action=positions", async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    attempts.push({
      key: route.request().headers()["idempotency-key"],
      body: route.request().postData(),
    });
    if (loseResponse) {
      loseResponse = false;
      const accepted = await route.fetch();
      expect(accepted.status()).toBe(201);
      const body = await accepted.json();
      savedId = body.position_id;
      accountId = body.account_id;
      await route.abort("failed");
    } else await route.continue();
  });
  await saveButton.click();
  await expect(
    page.getByRole("alert").filter({ hasText: "receipt key is retained" }),
  ).toContainText("receipt key is retained");
  await expect(saveButton).toBeEnabled();
  await saveButton.click();
  await expect(
    page.getByRole("button", { name: "Saved — reopen below", exact: true }),
  ).toBeVisible({ timeout: 30000 });
  expect(attempts).toHaveLength(2);
  expect(attempts[0]).toEqual(attempts[1]);
  expect(attempts[0].key).toMatch(/^[0-9a-f-]{36}$/);
  const records = await (
    await request.get(
      `/api/cfd-journal?action=positions&account_id=${accountId}&limit=100`,
    )
  ).json();
  expect(
    records.items.filter(
      (item: { position_id: string }) => item.position_id === savedId,
    ),
  ).toHaveLength(1);
});

test("CFD journal bridge rejects unsafe operations and foreign origins", async ({
  request,
}) => {
  const foreign = await request.get("/api/cfd-journal?action=status", {
    headers: { Origin: "https://untrusted.example" },
  });
  expect(foreign.status()).toBe(403);
  expect(
    (await request.get("/api/cfd-journal?action=positions")).status(),
  ).toBe(400);
  expect(
    (
      await request.get("/api/cfd-journal?action=status&action=examples")
    ).status(),
  ).toBe(400);
  expect(
    (await request.get("/api/cfd-journal?action=../../positions")).status(),
  ).toBe(404);
  expect(
    (
      await request.post("/api/cfd-journal?action=positions", { data: {} })
    ).status(),
  ).toBe(400);
  expect(
    (await request.delete("/api/cfd-journal?action=positions")).status(),
  ).toBe(405);
});
