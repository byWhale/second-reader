"use client";

import * as React from "react";
import { GripVerticalIcon } from "lucide-react";
import * as ResizablePrimitive from "react-resizable-panels";

import { cn } from "./utils";

function ResizablePanelGroup({
  className,
  ...props
}: React.ComponentProps<typeof ResizablePrimitive.PanelGroup>) {
  return (
    <ResizablePrimitive.PanelGroup
      data-slot="resizable-panel-group"
      className={cn(
        "flex h-full w-full data-[panel-group-direction=vertical]:flex-col",
        className,
      )}
      {...props}
    />
  );
}

function ResizablePanel({
  ...props
}: React.ComponentProps<typeof ResizablePrimitive.Panel>) {
  return <ResizablePrimitive.Panel data-slot="resizable-panel" {...props} />;
}

function ResizableHandle({
  withHandle,
  className,
  ...props
}: React.ComponentProps<typeof ResizablePrimitive.PanelResizeHandle> & {
  withHandle?: boolean;
}) {
  return (
    <ResizablePrimitive.PanelResizeHandle
      data-slot="resizable-handle"
      className={cn(
        "group focus-visible:ring-ring relative flex w-[7px] shrink-0 items-center justify-center bg-[linear-gradient(180deg,rgba(250,247,242,0.95),rgba(240,232,216,0.88))] focus-visible:ring-1 focus-visible:ring-offset-1 focus-visible:outline-hidden after:absolute after:inset-y-3 after:left-1/2 after:w-px after:-translate-x-1/2 after:rounded-full after:bg-[var(--warm-300)]/44 after:transition-colors hover:after:bg-[var(--amber-accent)]/32 data-[resize-handle-state=drag]:after:bg-[var(--amber-accent)]/52 data-[panel-group-direction=vertical]:h-[7px] data-[panel-group-direction=vertical]:w-full data-[panel-group-direction=vertical]:after:inset-x-3 data-[panel-group-direction=vertical]:after:top-1/2 data-[panel-group-direction=vertical]:after:h-px data-[panel-group-direction=vertical]:after:w-auto data-[panel-group-direction=vertical]:after:-translate-y-1/2 data-[panel-group-direction=vertical]:after:translate-x-0 [&[data-panel-group-direction=vertical]>div]:rotate-90",
        className,
      )}
      {...props}
    >
      {withHandle && (
        <div className="pointer-events-none z-10 flex h-8 w-4 items-center justify-center rounded-full border border-[var(--warm-300)]/65 bg-[var(--warm-50)]/96 text-[var(--warm-500)] opacity-0 shadow-[0_10px_28px_rgba(61,46,31,0.08)] transition-all duration-150 group-hover:opacity-100 group-data-[resize-handle-state=drag]:opacity-100 group-data-[resize-handle-state=drag]:text-[var(--amber-accent)]">
          <GripVerticalIcon className="size-2.5" />
        </div>
      )}
    </ResizablePrimitive.PanelResizeHandle>
  );
}

export { ResizablePanelGroup, ResizablePanel, ResizableHandle };
