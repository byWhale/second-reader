import { Outlet, Link, useLocation } from "react-router";
import { BookOpen, Library, Bookmark } from "lucide-react";

export function RootLayout() {
  const location = useLocation();
  const isLanding = location.pathname === "/";
  const marksActive = location.pathname === "/marks" || location.pathname === "/bookshelf/marks";
  const booksActive =
    !marksActive && (
    location.pathname.startsWith("/books") ||
    location.pathname.startsWith("/bookshelf") ||
    location.pathname.startsWith("/books/") ||
    location.pathname.startsWith("/upload") ||
    location.pathname.startsWith("/sample")
    );

  return (
    <div className="min-h-screen bg-[var(--warm-100)]">
      {/* Navigation */}
      <nav className={`sticky top-0 z-50 backdrop-blur-md ${isLanding ? "bg-transparent" : "bg-[var(--warm-100)]/90 border-b border-[var(--warm-300)]/40"}`}>
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 no-underline">
            <div className="w-8 h-8 rounded-lg bg-[var(--amber-accent)] flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-white" />
            </div>
            <span className="font-['Lora',Georgia,serif] text-[var(--warm-900)] tracking-tight" style={{ fontSize: '1.125rem', fontWeight: 600 }}>
              DeepRead
            </span>
          </Link>

          <div className="flex items-center gap-6">
            <Link
              to="/books"
              className={`flex items-center gap-1.5 no-underline transition-colors ${
                booksActive
                  ? "text-[var(--amber-accent)]"
                  : "text-[var(--warm-600)] hover:text-[var(--warm-800)]"
              }`}
              style={{ fontSize: '0.875rem' }}
            >
              <Library className="w-4 h-4" />
              Bookshelf
            </Link>
            <Link
              to="/marks"
              className={`flex items-center gap-1.5 no-underline transition-colors ${
                marksActive
                  ? "text-[var(--amber-accent)]"
                  : "text-[var(--warm-600)] hover:text-[var(--warm-800)]"
              }`}
              style={{ fontSize: '0.875rem' }}
            >
              <Bookmark className="w-4 h-4" />
              My Marks
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main>
        <Outlet />
      </main>
    </div>
  );
}
