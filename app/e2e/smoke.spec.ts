import { expect, test, type Page } from "@playwright/test";

// Every page must render real charts from the committed data, with no console errors and no horizontal scroll.
const PAGES = [
  { path: "/#/", heading: /Prices in the euro area were/ },
  { path: "/#/basket", heading: /Your basket, official prices/ },
  { path: "/#/quintiles", heading: /lowest-income fifth/ },
  { path: "/#/forecasts", heading: /Where inflation in the euro area is heading/ },
  { path: "/#/method", heading: /Method & sources/ },
];

function watchErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(e.message));
  return errors;
}

for (const p of PAGES) {
  test(`renders ${p.path}`, async ({ page }) => {
    const errors = watchErrors(page);
    await page.goto(p.path);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(p.heading);
    if (p.path !== "/#/method") await expect(page.locator("figure svg, [role=img] svg").first()).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
    expect(errors).toEqual([]);
  });
}

test("every chart card offers a measure-type badge", async ({ page }) => {
  await page.goto("/#/");
  await expect(page.getByRole("heading", { name: /Thirteen categories/ })).toBeVisible(); // last card loaded
  const cards = await page.locator("section:has(h2)").count();
  const badged = await page.locator("section:has(h2):has(span.uppercase)").count();
  expect(badged).toBe(cards);
});

test("changing country updates the Atlas headline", async ({ page }) => {
  await page.goto("/#/");
  await page.getByLabel("Country or area").selectOption("DE");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Prices in Germany were");
});

test("basket preset changes the result and stays private", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", (r) => requests.push(r.url()));
  await page.goto("/#/basket?geo=DE");
  const stat = page.getByText(/^Your basket since/).locator("..").locator(".font-serif");
  await expect(stat).toBeVisible();
  const before = await stat.textContent();
  await page.getByLabel("Start from").selectOption("QU1");
  await expect(stat).not.toHaveText(before ?? "");
  // nothing typed into the basket may leave the browser: only static data files are requested
  expect(requests.filter((u) => !u.startsWith("http://127.0.0.1:4181/"))).toEqual([]);
});

test("empty basket is rejected with a message, not a zero index", async ({ page }) => {
  await page.goto("/#/basket?geo=FR");
  await page.getByLabel("Start from").selectOption("equal");
  for (const input of await page.locator('input[type="number"][id^="w-"]').all()) await input.fill("0");
  await expect(page.getByRole("status")).toContainText("The basket is empty");
});

test("theme toggle switches to dark", async ({ page }) => {
  await page.goto("/#/method");
  await page.getByRole("button", { name: /Switch to dark theme/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
