"use client";

import * as React from "react";

export type ResponsiveTier = "wide" | "desktop" | "compact" | "narrow" | "mobile";

function resolveWidth(width: number): ResponsiveTier {
  if (width < 768) {
    return "mobile";
  }
  if (width < 840) {
    return "narrow";
  }
  if (width < 1024) {
    return "compact";
  }
  if (width < 1280) {
    return "desktop";
  }
  return "wide";
}

export function resolveResponsiveTier(width: number): ResponsiveTier {
  return resolveWidth(width);
}

export function useViewportResponsiveTier() {
  const [width, setWidth] = React.useState(() => (typeof window === "undefined" ? 0 : window.innerWidth));

  React.useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const measure = () => {
      setWidth(window.innerWidth);
    };

    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  return {
    width,
    tier: resolveWidth(width),
  };
}

export function useElementResponsiveTier<T extends HTMLElement>() {
  const [node, setNode] = React.useState<T | null>(null);
  const [width, setWidth] = React.useState(() => (typeof window === "undefined" ? 0 : window.innerWidth));

  const ref = React.useCallback((nextNode: T | null) => {
    setNode(nextNode);
  }, []);

  React.useEffect(() => {
    if (!node) {
      return;
    }

    const measure = () => {
      setWidth(node.getBoundingClientRect().width);
    };

    measure();

    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", measure);
      return () => window.removeEventListener("resize", measure);
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        measure();
        return;
      }
      setWidth(entry.contentRect.width);
    });

    observer.observe(node);
    return () => observer.disconnect();
  }, [node]);

  return {
    ref,
    width,
    tier: resolveWidth(width),
  };
}
