import { expect, test } from "@playwright/test";

test("landing page loads without horizontal overflow and has accessible actions", async ({ page }) => {
  await page.goto("/");
  console.log("landing:navigated");
  await expect(page).toHaveTitle(/SEO/i);
  await expect(page.getByRole("button", { name: /entrar/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /experimentar grátis/i })).toBeVisible();

  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
  console.log("landing:layout-checked");

  const visualState = await page.getByRole("heading", { level: 1 }).evaluate((element) => {
    const style = getComputedStyle(element);
    return { fontSize: Number.parseFloat(style.fontSize), color: style.color };
  });
  expect(visualState.fontSize).toBeGreaterThan(30);
  expect(visualState.color).not.toBe("rgba(0, 0, 0, 0)");
  console.log("landing:visual-checked");
});
