import { useState } from "react";
import { useNavigate } from "react-router";
import { fetchJobStatus, getErrorMessage, startBookAnalysis, type JobStatusResponse, uploadEpub } from "./api";
import { canonicalBookPath } from "./contract";

type DeferredConfirmation = {
  bookId: number;
  title: string;
  totalChapters: number;
};

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function waitForJob(
  jobId: string,
  predicate: (job: JobStatusResponse) => boolean,
  timeoutMs = 90_000,
): Promise<JobStatusResponse> {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    const job = await fetchJobStatus(jobId);
    if (job.status === "error") {
      throw new Error(job.last_error?.message ?? "Upload failed.");
    }
    if (predicate(job)) {
      return job;
    }
    await sleep(800);
  }

  throw new Error("The upload is taking longer than expected.");
}

export function useUploadBookActions(options: { onDeferredReady?: () => void } = {}) {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [statusText, setStatusText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<DeferredConfirmation | null>(null);

  async function runImmediateUpload(file: File) {
    setSubmitting(true);
    setStatusText("Uploading EPUB...");
    setError(null);
    try {
      const accepted = await uploadEpub(file, { startMode: "immediate" });
      setStatusText("Preparing for deep reading...");
      const readyJob =
        accepted.book_id != null
          ? { book_id: accepted.book_id }
          : await waitForJob(accepted.job_id, (job) => job.book_id != null && job.status !== "ready");
      navigate(canonicalBookPath(readyJob.book_id), { replace: true });
      return true;
    } catch (reason) {
      setError(getErrorMessage(reason));
      return false;
    } finally {
      setSubmitting(false);
      setStatusText(null);
    }
  }

  async function runDeferredUpload(file: File) {
    setSubmitting(true);
    setStatusText("Uploading EPUB...");
    setError(null);
    try {
      const accepted = await uploadEpub(file, { startMode: "deferred" });
      setStatusText("Parsing book structure...");
      const readyJob = await waitForJob(accepted.job_id, (job) => job.status === "ready" && job.book_id != null);
      const nextConfirmation = {
        bookId: readyJob.book_id as number,
        title: readyJob.book_title ?? file.name.replace(/\.epub$/i, ""),
        totalChapters: readyJob.total_chapters ?? 0,
      };
      setConfirmation(nextConfirmation);
      options.onDeferredReady?.();
      return nextConfirmation;
    } catch (reason) {
      setError(getErrorMessage(reason));
      return null;
    } finally {
      setSubmitting(false);
      setStatusText(null);
    }
  }

  async function confirmStartNow() {
    if (!confirmation) {
      return;
    }
    setSubmitting(true);
    setStatusText("Starting deep reading...");
    setError(null);
    try {
      await startBookAnalysis(confirmation.bookId);
      options.onDeferredReady?.();
      navigate(canonicalBookPath(confirmation.bookId), { replace: true });
      setConfirmation(null);
    } catch (reason) {
      setError(getErrorMessage(reason));
    } finally {
      setSubmitting(false);
      setStatusText(null);
    }
  }

  function decideLater() {
    setConfirmation(null);
    setError(null);
    options.onDeferredReady?.();
  }

  return {
    confirmation,
    error,
    setError,
    statusText,
    submitting,
    runImmediateUpload,
    runDeferredUpload,
    confirmStartNow,
    decideLater,
  };
}
