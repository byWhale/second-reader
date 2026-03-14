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

test("landing upload flows into canonical overview and chapter reading", async ({ page }) => {
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

  await page.getByTestId("landing-upload-cta").click();
  await expect(page.getByTestId("landing-upload-dialog")).toBeVisible();
  await page.getByTestId("landing-upload-input").setInputFiles(uploadFixture);
  await expect(page).toHaveURL(/\/books\/\d+$/);
  assertNoLegacyPath(new URL(page.url()).pathname);
  await expect(page.getByRole("heading", { name: "Fixture E2E Book" })).toBeVisible();

  const completedCard = page.getByTestId("analysis-completed-1");
  await expect(completedCard).toBeVisible({ timeout: 15_000 });
  await completedCard.click();
  await expect(page).toHaveURL(/\/books\/\d+\/chapters\/1$/);
  assertNoLegacyPath(new URL(page.url()).pathname);
  await expect(page.getByTestId("source-reader-pane")).toBeVisible();
  await expect(page.getByTestId("chapter-topbar")).toBeVisible();
  const chapterUrl = page.url();

  const reactionCard = page.locator('[data-testid^="reaction-card-"]').first();
  await expect(reactionCard).toBeVisible();
  const reactionTestId = await reactionCard.getAttribute("data-testid");
  const reactionId = reactionTestId?.replace("reaction-card-", "");
  expect(reactionId).toBeTruthy();
  await reactionCard.click();
  await expect(page).toHaveURL(new RegExp(`/books/\\d+/chapters/1\\?reaction=${reactionId}`));

  await page.goto("/books");
  await expect(page).toHaveURL(/\/books$/);
  await expect(page.getByTestId("global-nav-books")).toHaveAttribute("aria-current", "page");
  const bookCard = page.locator('[data-testid^="book-card-"]').first();
  const bookHref = await bookCard.getAttribute("href");
  expect(bookHref).toMatch(/^\/books\/\d+$/);
  await bookCard.click();
  await expect(page).toHaveURL(/\/books\/\d+$/);
  await expect(page.getByTestId("book-overview-source-download")).toBeVisible();

  await page.goto(chapterUrl);
  await page.getByTestId("brand-link").click();
  await expect(page).toHaveURL(/\/$/);

  expect(requestedPaths).not.toContain("/api/landing");
  expect(requestedPaths).not.toContain("/api/sample");
});

test("bookshelf upload supports defer-start and compat redirects", async ({ page }) => {
  await page.goto("/upload");
  await expect(page).toHaveURL(/\/books(?:\?.*)?$/);
  await expect(page.getByTestId("bookshelf-upload-dialog")).toContainText("添加一本新书");

  await page.getByTestId("bookshelf-upload-input").setInputFiles(uploadFixture);

  await expect(page.getByRole("alertdialog")).toContainText("已添加到书架", { timeout: 15_000 });
  await page.getByRole("button", { name: "稍后再说" }).click();
  await expect(page).toHaveURL(/\/books$/);

  const bookCard = page.locator('[data-testid^="book-card-"]').first();
  await expect(bookCard).toContainText("未开始");
  await bookCard.click();
  await expect(page).toHaveURL(/\/books\/\d+$/);
  assertNoLegacyPath(new URL(page.url()).pathname);
  await expect(page.getByRole("button", { name: "开始深读" })).toBeVisible();
  const bookUrl = page.url();

  await page.goto(`${bookUrl}/analysis`);
  await expect(page).toHaveURL(bookUrl);

  await page.getByRole("button", { name: "开始深读" }).click();
  await expect(page.getByText("分析中")).toBeVisible();
  await expect(page.getByTestId("analysis-completed-1")).toBeVisible({ timeout: 15_000 });
});
