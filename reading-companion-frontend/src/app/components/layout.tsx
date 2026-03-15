import { BookOpen, Bookmark, Library } from "lucide-react";
import { useEffect } from "react";
import { Link, Outlet, useLocation } from "react-router";
import { BRAND_CONFIG, getDocumentTitle } from "../config/brand";
import { copy } from "../config/controlled-copy";
import { term } from "../config/product-lexicon";
import { useViewportResponsiveTier } from "./ui/use-responsive-tier";

export function RootLayout() {
  const location = useLocation();
  const isLanding = location.pathname === "/";
  const isChapterWorkspace = /^\/books\/[^/]+\/chapters\/[^/]+$/.test(location.pathname);
  const booksActive = location.pathname === "/books" || location.pathname === "/bookshelf";
  const marksActive = location.pathname === "/marks" || location.pathname === "/bookshelf/marks";
  const brandHref = "/";
  const { tier: viewportTier } = useViewportResponsiveTier();
  const navCompact = viewportTier === "compact" || viewportTier === "narrow" || viewportTier === "mobile";
  const navNarrow = viewportTier === "narrow" || viewportTier === "mobile";

  useEffect(() => {
    document.title = getDocumentTitle(location.pathname);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-[var(--warm-100)]">
      <nav className={`sticky top-0 z-50 backdrop-blur-md ${isLanding ? "bg-[var(--warm-50)]/72" : "bg-[var(--warm-50)]/94 border-b border-[var(--warm-300)]/40"}`}>
        <div
          className={`py-3.5 ${
            isLanding
              ? "w-full px-6 md:px-8 xl:px-10"
              : isChapterWorkspace
                ? "w-full px-6"
                : "max-w-7xl mx-auto px-6"
          }`}
        >
          <div className={`flex items-center justify-between ${navCompact ? "gap-3" : "gap-4 flex-wrap sm:flex-nowrap"}`}>
            <div className="flex items-center gap-3 shrink-0">
              <Link to={brandHref} data-testid="brand-link" className="flex items-center gap-3 no-underline">
                <div className="w-10 h-10 rounded-xl bg-[var(--amber-accent)] flex items-center justify-center shadow-sm">
                  <BookOpen className="w-4.5 h-4.5 text-white" />
                </div>
                <div className="min-w-0">
                  <span className="block font-['Lora',Georgia,serif] text-[var(--warm-900)] tracking-tight" style={{ fontSize: "1.2rem", fontWeight: 600 }}>
                    {BRAND_CONFIG.productName}
                  </span>
                  {isLanding ? (
                    <span className="block text-[var(--warm-500)]" style={{ fontSize: "0.72rem", lineHeight: 1.1 }}>
                      {copy("layout.tagline")}
                    </span>
                  ) : null}
                </div>
              </Link>
            </div>

            {!isLanding ? (
              <div className={`rounded-full border border-[var(--warm-300)]/50 bg-white/78 shadow-sm ${navCompact ? "p-0.5" : "p-1"}`}>
                <div className="flex items-center gap-1">
                  <Link
                    to="/books"
                    data-testid="global-nav-books"
                    aria-current={booksActive ? "page" : undefined}
                    className={`inline-flex h-9 items-center gap-2 rounded-full px-4 no-underline transition-colors ${
                      booksActive
                        ? "bg-[var(--amber-bg)] text-[var(--amber-accent)]"
                        : "text-[var(--warm-600)] hover:bg-[var(--warm-100)] hover:text-[var(--warm-800)]"
                    } ${navCompact ? "h-8 gap-1.5 px-3" : "h-9 gap-2 px-4"}`}
                    style={{ fontSize: navCompact ? "0.79rem" : "0.875rem", fontWeight: 600 }}
                  >
                    <Library className="w-4 h-4" />
                    {navNarrow ? copy("page.books.title") : BRAND_CONFIG.navigation.booksLabel}
                  </Link>
                  <Link
                    to="/marks"
                    data-testid="global-nav-marks"
                    aria-current={marksActive ? "page" : undefined}
                    className={`inline-flex h-9 items-center gap-2 rounded-full px-4 no-underline transition-colors ${
                      marksActive
                        ? "bg-[var(--amber-bg)] text-[var(--amber-accent)]"
                        : "text-[var(--warm-600)] hover:bg-[var(--warm-100)] hover:text-[var(--warm-800)]"
                    } ${navCompact ? "h-8 gap-1.5 px-3" : "h-9 gap-2 px-4"}`}
                    style={{ fontSize: navCompact ? "0.79rem" : "0.875rem", fontWeight: 600 }}
                  >
                    <Bookmark className="w-4 h-4" />
                    {navNarrow ? term("nav.marks") : BRAND_CONFIG.navigation.marksLabel}
                  </Link>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </nav>

      <main>
        <Outlet />
      </main>
    </div>
  );
}
