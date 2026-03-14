import { AlertTriangle, ArrowRight, BookOpen, CheckCircle2, LoaderCircle, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { BookShelfCard, fetchBooks, toApiAssetUrl, toFrontendPath } from "../lib/api";
import { useApiResource } from "../lib/use-api-resource";
import { useUploadBookActions } from "../lib/use-upload-book-actions";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "./ui/alert-dialog";
import { EmptyState, ErrorState, LoadingState } from "./page-state";
import { ImageWithFallback } from "./figma/ImageWithFallback";
import { UploadBookDialog } from "./upload-book-dialog";

const statusMeta: Record<BookShelfCard["reading_status"], { label: string; icon: typeof BookOpen; color: string }> = {
  not_started: { label: "未开始", icon: BookOpen, color: "text-[var(--warm-500)]" },
  analyzing: { label: "分析中", icon: LoaderCircle, color: "text-[var(--amber-accent)]" },
  paused: { label: "已暂停，可继续", icon: AlertTriangle, color: "text-[var(--amber-accent)]" },
  completed: { label: "已完成", icon: CheckCircle2, color: "text-green-700" },
  error: { label: "需要处理", icon: AlertTriangle, color: "text-[var(--destructive)]" },
};

function statusSummary(book: BookShelfCard) {
  if (book.reading_status === "analyzing") {
    return `${statusMeta[book.reading_status].label} · ${book.completed_chapters}/${book.total_chapters} 章`;
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
        <h2 className="text-[var(--warm-900)] mb-1 line-clamp-2" style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.4 }}>
          {book.title}
        </h2>
        <p className="text-[var(--warm-600)] mb-3" style={{ fontSize: "0.8125rem" }}>
          {book.author}
        </p>

        <div className="flex items-center justify-between gap-3 mb-3">
          <div className={`flex items-center gap-1.5 ${status.color}`} style={{ fontSize: "0.75rem", fontWeight: 500 }}>
            <Icon className={`w-3.5 h-3.5 ${book.reading_status === "analyzing" ? "animate-spin" : ""}`} />
            <span>{statusSummary(book)}</span>
          </div>
        </div>

        <div className="flex items-center justify-between text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
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
    return (
      <ErrorState
        title="Bookshelf is unavailable"
        message={error ?? "We could not load your books right now."}
        onRetry={reload}
        linkLabel="Upload a book"
        linkTo="/books?upload=1"
      />
    );
  }

  return (
    <>
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
            <button
              type="button"
              onClick={openUploadDialog}
              data-testid="bookshelf-open-upload"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--amber-accent)] text-white hover:bg-[var(--warm-700)] transition-colors cursor-pointer"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              <Upload className="w-4 h-4" />
              添加新书
            </button>
          </div>
        </div>

        {data.items.length === 0 ? (
          <EmptyState
            title="No books yet"
            message="Upload an EPUB to add the first book to this workspace."
            actionLabel="添加新书"
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
        title="添加一本新书"
        description="上传 EPUB 文件，书虫会解析全书结构，准备好后可以随时开始深读。"
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
              《{uploadActions.confirmation?.title ?? "这本书"}》已添加到书架
            </AlertDialogTitle>
            <AlertDialogDescription>
              原书目录已解析完成，共 {uploadActions.confirmation?.totalChapters ?? 0} 章。要现在开始深读，还是先只进入书架？
            </AlertDialogDescription>
          </AlertDialogHeader>
          {uploadActions.error ? (
            <p className="text-[var(--destructive)]" style={{ fontSize: "0.8125rem" }}>
              {uploadActions.error}
            </p>
          ) : null}
          <AlertDialogFooter>
            <AlertDialogCancel onClick={uploadActions.decideLater}>只进入书架</AlertDialogCancel>
            <AlertDialogAction onClick={() => void uploadActions.confirmStartNow()} data-testid="bookshelf-confirm-start-reading">
              开始深读 →
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
