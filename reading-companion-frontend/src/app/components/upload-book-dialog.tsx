"use client";

import { FileText, LoaderCircle, Upload, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { copy } from "../config/controlled-copy";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "./ui/dialog";

type UploadBookDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onFileSelected: (file: File) => Promise<void> | void;
  title: string;
  description?: string;
  inputTestId: string;
  dialogTestId?: string;
  statusText?: string | null;
  error?: string | null;
  submitting?: boolean;
};

export function UploadBookDialog({
  open,
  onOpenChange,
  onFileSelected,
  title,
  description,
  inputTestId,
  dialogTestId,
  statusText,
  error,
  submitting = false,
}: UploadBookDialogProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      return;
    }
    setIsDragging(false);
    setFileName(null);
  }, [open]);

  async function handleFile(file: File | null) {
    if (!file) {
      return;
    }
    setFileName(file.name);
    await onFileSelected(file);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (submitting && !nextOpen) {
          return;
        }
        onOpenChange(nextOpen);
      }}
    >
      <DialogContent
        data-testid={dialogTestId}
        overlayClassName="bg-black/25 backdrop-blur-[2px]"
        showCloseButton={false}
        className="w-full max-w-[calc(100%-2rem)] overflow-hidden border-[var(--warm-300)]/20 bg-[#FFFCF8] p-0 shadow-2xl sm:max-w-[26.25rem]"
      >
        <div className="rounded-2xl">
          <div className="flex items-start justify-between gap-4 px-6 pt-5 pb-0">
            <DialogHeader className="gap-2 text-left">
              <DialogTitle
                className="font-['Lora',Georgia,serif] text-[var(--warm-900)]"
                style={{ fontSize: "1.125rem", fontWeight: 600, lineHeight: 1.2 }}
              >
                {title}
              </DialogTitle>
              {description ? (
                <DialogDescription
                  className="max-w-[21rem] text-[var(--warm-600)]"
                  style={{ fontSize: "0.75rem", lineHeight: 1.5 }}
                >
                  {description}
                </DialogDescription>
              ) : null}
            </DialogHeader>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              disabled={submitting}
              aria-label={copy("upload.dialog.close")}
              className="inline-flex h-7 w-7 items-center justify-center rounded-full transition-colors hover:bg-[var(--warm-200)] disabled:cursor-not-allowed disabled:opacity-40"
            >
              <X className="h-4 w-4 text-[var(--warm-500)]" strokeWidth={1.6} />
            </button>
          </div>

          <div className="px-6 pt-4 pb-5">
            <div
              role="button"
              tabIndex={0}
              onClick={() => inputRef.current?.click()}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  inputRef.current?.click();
                }
              }}
              onDragEnter={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragOver={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={(event) => {
                event.preventDefault();
                const nextTarget = event.relatedTarget;
                if (nextTarget instanceof Node && event.currentTarget.contains(nextTarget)) {
                  return;
                }
                setIsDragging(false);
              }}
              onDrop={(event) => {
                event.preventDefault();
                setIsDragging(false);
                void handleFile(event.dataTransfer.files?.[0] ?? null);
              }}
              className={[
                "group relative flex min-h-[16rem] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-all duration-200",
                isDragging
                  ? "scale-[1.01] border-[var(--amber-accent)] bg-[var(--amber-bg)]"
                  : "border-[var(--warm-300)] bg-[var(--warm-100)]/50 hover:border-[var(--warm-400)] hover:bg-[var(--warm-100)]",
                submitting ? "pointer-events-none opacity-85" : "",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".epub,application/epub+zip"
                data-testid={inputTestId}
                className="sr-only"
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  void handleFile(file);
                  event.currentTarget.value = "";
                }}
              />

              <div
                className={[
                  "mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full transition-colors duration-200",
                  isDragging ? "bg-[var(--amber-accent)]/15" : "bg-[var(--warm-200)]",
                ].join(" ")}
              >
                {submitting ? (
                  <LoaderCircle className={`h-5 w-5 animate-spin ${isDragging ? "text-[var(--amber-accent)]" : "text-[var(--warm-500)]"}`} />
                ) : (
                  <Upload className={`h-5 w-5 ${isDragging ? "text-[var(--amber-accent)]" : "text-[var(--warm-500)]"}`} strokeWidth={1.75} />
                )}
              </div>

              <div className="space-y-1">
                <p
                  className="text-[var(--warm-800)]"
                  style={{ fontSize: "0.9375rem", fontWeight: 500, lineHeight: 1.3 }}
                >
                  {isDragging ? copy("upload.dialog.dropActive") : copy("upload.dialog.drop")}
                </p>
                <p className="text-[var(--warm-500)]" style={{ fontSize: "0.8125rem", lineHeight: 1.45 }}>
                  {isDragging ? (
                    copy("upload.dialog.release")
                  ) : (
                    <>
                      or{" "}
                      <span className="text-[var(--amber-accent)] underline underline-offset-2">
                        {copy("upload.dialog.browse")}
                      </span>
                    </>
                  )}
                </p>
              </div>

              {fileName ? (
                <p className="mt-3 max-w-full truncate text-[var(--warm-600)]" style={{ fontSize: "0.75rem" }}>
                  {fileName}
                </p>
              ) : null}
              {statusText ? (
                <p className="mt-2 text-[var(--warm-600)]" style={{ fontSize: "0.75rem" }}>
                  {statusText}
                </p>
              ) : null}
              {error ? (
                <p className="mt-2 max-w-[16rem] text-[var(--destructive)]" style={{ fontSize: "0.75rem" }}>
                  {error}
                </p>
              ) : null}
            </div>

            <div className="mt-4 flex items-center justify-center gap-1.5">
              <FileText className="h-3.5 w-3.5 text-[var(--warm-400)]" />
              <span className="text-[var(--warm-400)]" style={{ fontSize: "0.75rem" }}>
                {copy("upload.dialog.supports")}
              </span>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
