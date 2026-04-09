import { AlertTriangle, ArrowRight, BookOpen, CheckCircle2, LoaderCircle, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { copy } from "../config/controlled-copy";
import { term } from "../config/product-lexicon";
import { BookShelfCard, fetchBooks, getErrorPresentation, toApiAssetUrl, toFrontendPath } from "../lib/api";
import { useApiResource } from "../lib/use-api-resource";
import { useUploadBookActions } from "../lib/use-upload-book-actions";
import { uiTypography } from "../lib/visual-system";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "./ui/alert-dialog";
import { EmptyState, ErrorState, LoadingState } from "./page-state";
import { ImageWithFallback } from "./figma/ImageWithFallback";
import { UploadBookDialog } from "./upload-book-dialog";

const statusMeta: Record<BookShelfCard["reading_status"], { label: string; icon: typeof BookOpen; color: string }> = {
  not_started: { label: term("state.notStarted"), icon: BookOpen, color: "text-[var(--warm-500)]" },
  analyzing: { label: term("state.analyzing"), icon: LoaderCircle, color: "text-[var(--amber-accent)]" },
  paused: { label: term("state.paused"), icon: AlertTriangle, color: "text-[var(--amber-accent)]" },
  completed: { label: term("state.completed"), icon: CheckCircle2, color: "text-green-700" },
  error: { label: term("state.needsAttention"), icon: AlertTriangle, color: "text-[var(--destructive)]" },
};

type RuntimeStatusReason = "runtime_stale" | "runtime_interrupted" | "resume_incompatible" | "dev_run_abandoned";

function readStatusReason(value: unknown): RuntimeStatusReason | null {
  const rawReason =
    value && typeof value === "object" && "status_reason" in value
      ? (value as { status_reason?: unknown }).status_reason
      : null;
  switch (rawReason) {
    case "runtime_stale":
    case "runtime_interrupted":
    case "resume_incompatible":
    case "dev_run_abandoned":
      return rawReason;
    default:
      return null;
  }
}

function statusSummary(book: BookShelfCard) {
  if (book.reading_status === "analyzing") {
    return `${statusMeta[book.reading_status].label} · ${book.completed_chapters}/${book.total_chapters} ${term("view.chapters").toLowerCase()}`;
  }
  if (book.reading_status === "paused") {
    switch (readStatusReason(book)) {
      case "runtime_stale":
        return copy("bookshelf.status.paused.runtimeStale");
      case "runtime_interrupted":
        return copy("bookshelf.status.paused.runtimeInterrupted");
      case "resume_incompatible":
        return copy("bookshelf.status.paused.resumeIncompatible");
      case "dev_run_abandoned":
        return copy("bookshelf.status.paused.devRunAbandoned");
      default:
        return statusMeta[book.reading_status].label;
    }
  }
  return statusMeta[book.reading_status].label;
}

function BookCard({ book }: { book: BookShelfCard }) {
  const status = statusMeta[book.reading_status];
  const Icon = status.icon;

  return (
    <Link
      to={toFrontendPath(book.open_target)}
      data-testid={`book-card-${book.book_id}`}
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
        <h2 className="text-[var(--warm-900)] mb-1 line-clamp-2" style={uiTypography.bodyStrong}>
          {book.title}
        </h2>
        <p className="text-[var(--warm-600)] mb-3" style={uiTypography.caption}>
          {book.author}
        </p>

        <div className="flex items-center justify-between gap-3 mb-3">
          <div className={`flex items-center gap-1.5 ${status.color}`} style={uiTypography.chip}>
            <Icon className={`w-3.5 h-3.5 ${book.reading_status === "analyzing" ? "animate-spin" : ""}`} />
            <span>{statusSummary(book)}</span>
          </div>
        </div>

        <div className="flex items-center justify-between text-[var(--warm-500)]" style={uiTypography.chip}>
          <span>
            {book.book_language} → {book.output_language}
          </span>
          <span>{book.mark_count} marks</span>
        </div>
      </div>
    </Link>
  );
}

export function BookshelfPage() {
  const { data, loading, error, reload } = useApiResource(fetchBooks, []);
  const [searchParams, setSearchParams] = useSearchParams();
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const uploadActions = useUploadBookActions({ onDeferredReady: reload });

  useEffect(() => {
    if (searchParams.get("upload") !== "1") {
      return;
    }
    setUploadDialogOpen(true);
    const next = new URLSearchParams(searchParams);
    next.delete("upload");
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  function openUploadDialog() {
    uploadActions.setError(null);
    setUploadDialogOpen(true);
  }

  if (loading) {
    return <LoadingState title="Loading your bookshelf..." />;
  }

  if (error || !data) {
    const errorState = getErrorPresentation(error, {
      title: copy("bookshelf.error.title"),
      message: copy("bookshelf.error.message"),
    });
    return (
      <ErrorState
        title={errorState.title}
        message={errorState.message}
        onRetry={reload}
        linkLabel={copy("bookshelf.action.addBook")}
        linkTo="/books?upload=1"
      />
    );
  }

  return (
    <>
      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between gap-4 mb-10 flex-wrap">
          <div>
            <h1 className="text-[var(--warm-900)] mb-1" style={uiTypography.pageTitle}>
              {copy("page.books.title")}
            </h1>
            <p className="text-[var(--warm-600)]" style={uiTypography.meta}>
              {copy("bookshelf.count.summary", { books: data.items.length, marks: data.global_mark_count })}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/marks"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--warm-300)]/60 text-[var(--warm-700)] no-underline hover:bg-[var(--warm-100)] transition-colors"
              style={uiTypography.control}
            >
              {copy("bookshelf.action.openMarks")}
              <ArrowRight className="w-4 h-4" />
            </Link>
            <button
              type="button"
              onClick={openUploadDialog}
              data-testid="bookshelf-open-upload"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--amber-accent)] text-white hover:bg-[var(--warm-700)] transition-colors cursor-pointer"
              style={uiTypography.control}
            >
              <Upload className="w-4 h-4" />
              {copy("bookshelf.action.addBook")}
            </button>
          </div>
        </div>

        {data.items.length === 0 ? (
          <EmptyState
            title={copy("bookshelf.empty.title")}
            message={copy("bookshelf.empty.message")}
            actionLabel={copy("bookshelf.action.addBook")}
            actionTo="/books?upload=1"
          />
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6">
            {data.items.map((book) => (
              <BookCard key={book.book_id} book={book} />
            ))}
          </div>
        )}
      </div>

      <UploadBookDialog
        open={uploadDialogOpen}
        onOpenChange={setUploadDialogOpen}
        onFileSelected={async (file) => {
          const result = await uploadActions.runDeferredUpload(file);
          if (result) {
            setUploadDialogOpen(false);
          }
        }}
        title={copy("bookshelf.upload.title")}
        description={copy("bookshelf.upload.description")}
        inputTestId="bookshelf-upload-input"
        dialogTestId="bookshelf-upload-dialog"
        statusText={uploadActions.statusText}
        error={uploadActions.error}
        submitting={uploadActions.submitting}
      />

      <AlertDialog open={uploadActions.confirmation != null}>
        <AlertDialogContent className="bg-[var(--warm-50)] border-[var(--warm-300)]/40">
          <AlertDialogHeader>
            <AlertDialogTitle>
              {copy("bookshelf.confirmation.title", {
                title: uploadActions.confirmation?.title ?? "This book",
              })}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {copy("bookshelf.confirmation.description", {
                count: uploadActions.confirmation?.totalChapters ?? 0,
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          {uploadActions.error ? (
            <p className="text-[var(--destructive)]" style={uiTypography.caption}>
              {uploadActions.error}
            </p>
          ) : null}
          <AlertDialogFooter>
            <AlertDialogCancel onClick={uploadActions.decideLater}>{copy("bookshelf.confirmation.later")}</AlertDialogCancel>
            <AlertDialogAction onClick={() => void uploadActions.confirmStartNow()} data-testid="bookshelf-confirm-start-reading">
              {copy("bookshelf.confirmation.start")} →
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
