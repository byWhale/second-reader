import { AlertTriangle, ArrowRight, BookOpen, CheckCircle2, LoaderCircle, Upload } from "lucide-react";
import { Link } from "react-router";
import { BookShelfCard, fetchBooks, toApiAssetUrl, toFrontendPath } from "../lib/api";
import { useApiResource } from "../lib/use-api-resource";
import { EmptyState, ErrorState, LoadingState } from "./page-state";
import { ImageWithFallback } from "./figma/ImageWithFallback";

const statusMeta: Record<BookShelfCard["reading_status"], { label: string; icon: typeof BookOpen; color: string }> = {
  not_started: { label: "Not started", icon: BookOpen, color: "text-[var(--warm-500)]" },
  analyzing: { label: "Analyzing", icon: LoaderCircle, color: "text-[var(--amber-accent)]" },
  completed: { label: "Completed", icon: CheckCircle2, color: "text-green-700" },
  error: { label: "Needs attention", icon: AlertTriangle, color: "text-[var(--destructive)]" },
};

function BookCard({ book }: { book: BookShelfCard }) {
  const status = statusMeta[book.reading_status];
  const Icon = status.icon;

  return (
    <Link
      to={toFrontendPath(book.open_target)}
      className="group bg-white rounded-2xl border border-[var(--warm-300)]/30 overflow-hidden shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all no-underline"
    >
      <div className="aspect-[3/4] bg-[var(--warm-200)] overflow-hidden">
        {book.cover_image_url ? (
          <ImageWithFallback
            src={toApiAssetUrl(book.cover_image_url) ?? ""}
            alt={book.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[var(--warm-500)]">
            <BookOpen className="w-10 h-10" />
          </div>
        )}
      </div>

      <div className="p-4">
        <h2 className="text-[var(--warm-900)] mb-1 line-clamp-2" style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.4 }}>
          {book.title}
        </h2>
        <p className="text-[var(--warm-600)] mb-3" style={{ fontSize: "0.8125rem" }}>
          {book.author}
        </p>

        <div className="flex items-center justify-between gap-3 mb-3">
          <div className={`flex items-center gap-1.5 ${status.color}`} style={{ fontSize: "0.75rem", fontWeight: 500 }}>
            <Icon className={`w-3.5 h-3.5 ${book.reading_status === "analyzing" ? "animate-spin" : ""}`} />
            <span>{status.label}</span>
          </div>
          <span className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
            {book.completed_chapters}/{book.total_chapters} ch.
          </span>
        </div>

        <div className="flex items-center justify-between text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
          <span>{book.book_language} → {book.output_language}</span>
          <span>{book.mark_count} marks</span>
        </div>
      </div>
    </Link>
  );
}

export function BookshelfPage() {
  const { data, loading, error, reload } = useApiResource(fetchBooks, []);

  if (loading) {
    return <LoadingState title="Loading bookshelf..." />;
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Bookshelf is unavailable"
        message={error ?? "The API did not return bookshelf data."}
        onRetry={reload}
        linkLabel="Upload a book"
        linkTo="/upload"
      />
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between gap-4 mb-10 flex-wrap">
        <div>
          <h1 className="text-[var(--warm-900)] mb-1" style={{ fontSize: "1.875rem", fontWeight: 600 }}>
            Books
          </h1>
          <p className="text-[var(--warm-600)]" style={{ fontSize: "0.875rem" }}>
            {data.items.length} books · {data.global_mark_count} total marks
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/marks"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--warm-300)]/60 text-[var(--warm-700)] no-underline hover:bg-[var(--warm-100)] transition-colors"
            style={{ fontSize: "0.875rem", fontWeight: 500 }}
          >
            My marks
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            to="/upload"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--amber-accent)] text-white no-underline hover:bg-[var(--warm-700)] transition-colors"
            style={{ fontSize: "0.875rem", fontWeight: 500 }}
          >
            <Upload className="w-4 h-4" />
            Upload EPUB
          </Link>
        </div>
      </div>

      {data.items.length === 0 ? (
        <EmptyState
          title="No books yet"
          message="Upload an EPUB to create the first analysis run in this workspace."
          actionLabel="Go to upload"
          actionTo="/upload"
        />
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6">
          {data.items.map((book) => (
            <BookCard key={book.book_id} book={book} />
          ))}
        </div>
      )}
    </div>
  );
}
