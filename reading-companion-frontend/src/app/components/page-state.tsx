import { AlertCircle, LoaderCircle } from "lucide-react";
import { Link } from "react-router";
import { copy } from "../config/controlled-copy";

export function LoadingState({ title = copy("state.loading.generic") }: { title?: string }) {
  return (
    <div className="max-w-4xl mx-auto px-6 py-16">
      <div className="bg-white rounded-2xl border border-[var(--warm-300)]/30 p-10 text-center shadow-sm">
        <LoaderCircle className="w-8 h-8 text-[var(--amber-accent)] mx-auto mb-3 animate-spin" />
        <p className="text-[var(--warm-700)]" style={{ fontSize: "0.9375rem" }}>
          {title}
        </p>
      </div>
    </div>
  );
}

export function ErrorState({
  title = copy("state.error.title"),
  message,
  retryLabel,
  onRetry,
  linkLabel,
  linkTo,
}: {
  title?: string;
  message: string;
  retryLabel?: string;
  onRetry?: () => void;
  linkLabel?: string;
  linkTo?: string;
}) {
  return (
    <div className="max-w-4xl mx-auto px-6 py-16">
      <div className="bg-white rounded-2xl border border-[var(--warm-300)]/30 p-10 text-center shadow-sm">
        <AlertCircle className="w-8 h-8 text-[var(--destructive)] mx-auto mb-3" />
        <h2 className="text-[var(--warm-900)] mb-2" style={{ fontSize: "1.125rem", fontWeight: 600 }}>
          {title}
        </h2>
        <p className="text-[var(--warm-600)] max-w-xl mx-auto" style={{ fontSize: "0.9375rem", lineHeight: 1.7 }}>
          {message}
        </p>
        <div className="flex items-center justify-center gap-3 mt-6">
          {onRetry ? (
            <button
              onClick={onRetry}
              className="px-4 py-2 rounded-lg bg-[var(--amber-accent)] text-white hover:bg-[var(--warm-700)] transition-colors cursor-pointer"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              {retryLabel ?? copy("action.retry")}
            </button>
          ) : null}
          {linkLabel && linkTo ? (
            <Link
              to={linkTo}
              className="px-4 py-2 rounded-lg border border-[var(--warm-300)]/50 text-[var(--warm-700)] no-underline hover:bg-[var(--warm-100)] transition-colors"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              {linkLabel}
            </Link>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  message,
  actionLabel,
  actionTo,
}: {
  title: string;
  message: string;
  actionLabel?: string;
  actionTo?: string;
}) {
  return (
    <div className="bg-white rounded-2xl border border-[var(--warm-300)]/30 p-10 text-center shadow-sm">
      <h2 className="text-[var(--warm-900)] mb-2" style={{ fontSize: "1.125rem", fontWeight: 600 }}>
        {title}
      </h2>
      <p className="text-[var(--warm-600)]" style={{ fontSize: "0.9375rem", lineHeight: 1.7 }}>
        {message}
      </p>
      {actionLabel && actionTo ? (
        <Link
          to={actionTo}
          className="inline-flex mt-5 px-4 py-2 rounded-lg bg-[var(--amber-accent)] text-white no-underline hover:bg-[var(--warm-700)] transition-colors"
          style={{ fontSize: "0.875rem", fontWeight: 500 }}
        >
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}
