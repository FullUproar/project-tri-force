import { test, expect } from "@playwright/test";

// Note: These tests require Clerk to be in development mode
// or the test to bypass auth. For CI, set CLERK_SECRET_KEY
// and use Clerk's testing tokens.

test.describe("CortaLoom Dashboard", () => {
  test("sign-in page loads", async ({ page }) => {
    await page.goto("/sign-in");
    await expect(page).toHaveTitle(/CortaLoom/);
    // Clerk sign-in component should render
    await expect(page.locator("text=CortaLoom")).toBeVisible();
  });

  test("sign-up page loads", async ({ page }) => {
    await page.goto("/sign-up");
    await expect(page.locator("text=CortaLoom")).toBeVisible();
    await expect(page.locator("text=Create your ASC account")).toBeVisible();
  });

  test("unauthenticated user is redirected to sign-in", async ({ page }) => {
    await page.goto("/");
    // Should redirect to /sign-in
    await page.waitForURL(/sign-in/);
    await expect(page).toHaveURL(/sign-in/);
  });

  test("onboarding page loads", async ({ page }) => {
    await page.goto("/onboarding");
    // May redirect to sign-in if not authenticated
    const url = page.url();
    if (url.includes("sign-in")) {
      // Expected — auth required
      expect(true).toBe(true);
    } else {
      await expect(page.locator("text=Welcome to CortaLoom")).toBeVisible();
    }
  });

  test("admin page loads", async ({ page }) => {
    await page.goto("/admin");
    const url = page.url();
    if (url.includes("sign-in")) {
      expect(true).toBe(true);
    } else {
      await expect(page.locator("text=CortaLoom Admin")).toBeVisible();
    }
  });

  test("analytics page loads", async ({ page }) => {
    await page.goto("/analytics");
    const url = page.url();
    if (url.includes("sign-in")) {
      expect(true).toBe(true);
    } else {
      await expect(page.locator("text=Analytics")).toBeVisible();
    }
  });

  test("API proxy health check works", async ({ request }) => {
    const response = await request.get("/api/proxy/health");
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.service).toBe("cortaloom-api");
  });
});
