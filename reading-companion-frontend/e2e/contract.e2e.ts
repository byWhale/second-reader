import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const uploadFixture = path.resolve(__dirname, "../../reading-companion-backend/tests/fixtures/e2e_runtime/sample-upload.epub");

function assertNoLegacyPath(pathname: string): void {
  expect(pathname.startsWith("/bookshelf")).toBeFalsy();
  expect(pathname.startsWith("/book/")).toBeFalsy();
  expect(pathname.startsWith("/analysis/")).toBeFalsy();
  expect(pathname.startsWith("/sample")).toBeFalsy();
}

test("fixture upload flow stays on canonical routes and persists marks", async ({ page }) => {
  const requestedPaths: string[] = [];
  page.on("request", (request) => {
    try {
      requestedPaths.push(new URL(request.url()).pathname);
    } catch {
      // ignore non-standard URLs
    }
  });

  await page.goto("/");
  await expect(page).toHaveURL(/\/$/);
  assertNoLegacyPath(new URL(page.url()).pathname);

  await page.goto("/upload");
  await expect(page).toHaveURL(/\/upload$/);
  await expect(page.getByTestId("global-nav-books")).not.toHaveAttribute("aria-current", "page");
  await expect(page.getByTestId("global-nav-marks")).not.toHaveAttribute("aria-current", "page");
  await page.getByTestId("upload-input").setInputFiles(uploadFixture);
  await page.getByTestId("upload-submit").click();

  const openCurrent = page.getByTestId("upload-open-current-result");
  await expect(openCurrent).toBeVisible({ timeout: 15_000 });
  await openCurrent.click();
  await expect(page).toHaveURL(/\/books\/\d+\/analysis$/);
  assertNoLegacyPath(new URL(page.url()).pathname);
  await expect(page.getByRole("heading", { name: "Fixture E2E Book" })).toBeVisible();

  const completedCard = page.getByTestId("analysis-completed-1");
  await expect(completedCard).toBeVisible({ timeout: 15_000 });
  const completedHref = await completedCard.getAttribute("href");
  expect(completedHref).toMatch(/^\/books\/\d+\/chapters\/1$/);
  await completedCard.click();
  await expect(page).toHaveURL(/\/books\/\d+\/chapters\/1$/);
  assertNoLegacyPath(new URL(page.url()).pathname);
  await expect(page.getByTestId("global-nav-books")).not.toHaveAttribute("aria-current", "page");
  await expect(page.getByTestId("global-nav-marks")).not.toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("link", { name: /Source EPUB/i })).toHaveCount(0);
  await expect(page.getByTestId("source-reader-pane")).toBeVisible();
  const chapterUrl = page.url();

  await page.goto("/books");
  await expect(page).toHaveURL(/\/books$/);
  await expect(page.getByTestId("global-nav-books")).toHaveAttribute("aria-current", "page");
  await expect(page.getByTestId("global-nav-marks")).not.toHaveAttribute("aria-current", "page");
  await expect(page.getByTestId("brand-overview-link")).toHaveCount(0);
  await page.getByTestId("brand-link").click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/books");
  await expect(page).toHaveURL(/\/books$/);
  const bookCard = page.locator('[data-testid^="book-card-"]').first();
  const bookHref = await bookCard.getAttribute("href");
  expect(bookHref).toMatch(/^\/books\/\d+$/);
  await bookCard.click();
  await expect(page).toHaveURL(/\/books\/\d+$/);
  assertNoLegacyPath(new URL(page.url()).pathname);
  await expect(page.getByTestId("global-nav-books")).not.toHaveAttribute("aria-current", "page");
  await expect(page.getByTestId("global-nav-marks")).not.toHaveAttribute("aria-current", "page");
  await expect(page.getByTestId("book-overview-source-download")).toBeVisible();

  const overviewChapter = page.getByTestId("book-overview-chapter-1");
  await expect(overviewChapter).toBeVisible();
  await overviewChapter.click();
  await expect(page).toHaveURL(/\/books\/\d+\/chapters\/1$/);
  expect(page.url()).toBe(chapterUrl);
  assertNoLegacyPath(new URL(page.url()).pathname);

  const reactionCard = page.locator('[data-testid^="reaction-card-"]').first();
  await expect(reactionCard).toBeVisible();
  const reactionTestId = await reactionCard.getAttribute("data-testid");
  const reactionId = reactionTestId?.replace("reaction-card-", "");
  expect(reactionId).toBeTruthy();
  await reactionCard.click();
  await expect(page).toHaveURL(new RegExp(`/books/\\d+/chapters/1\\?reaction=${reactionId}`));
  await expect(page.getByTestId("reader-current-target")).toHaveText(/\S+/);

  await page.goto(`${chapterUrl}?reaction=${reactionId}`);
  await expect(page).toHaveURL(new RegExp(`/books/\\d+/chapters/1\\?reaction=${reactionId}`));
  await expect(page.getByTestId("source-reader-pane")).toBeVisible();

  await page.getByTestId(`mark-resonance-${reactionId}`).click();
  await page.goto("/marks");
  await expect(page).toHaveURL(/\/marks$/);
  assertNoLegacyPath(new URL(page.url()).pathname);
  const markCard = page.locator('[data-testid^="global-mark-"]').first();
  await expect(markCard).toContainText("resonance");

  await page.goto(chapterUrl);
  await page.getByTestId(`mark-blindspot-${reactionId}`).click();
  await page.goto("/marks");
  await expect(page.locator('[data-testid^="global-mark-"]').first()).toContainText("blindspot");

  await page.goto(chapterUrl);
  await page.getByTestId(`mark-bookmark-${reactionId}`).click();
  await page.goto("/marks");
  await expect(page.locator('[data-testid^="global-mark-"]').first()).toContainText("bookmark");

  await page.goto(chapterUrl);
  await page.getByTestId("brand-link").click();
  await expect(page).toHaveURL(/\/$/);

  expect(requestedPaths).not.toContain("/api/landing");
  expect(requestedPaths).not.toContain("/api/sample");
});
