import { DependencyList, startTransition, useEffect, useState } from "react";

export function useApiResource<T>(loader: () => Promise<T>, deps: DependencyList) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown | null>(null);
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    let active = true;

    setLoading(true);
    setError(null);

    loader()
      .then((value) => {
        if (!active) {
          return;
        }
        startTransition(() => {
          setData(value);
        });
      })
      .catch((reason) => {
        if (!active) {
          return;
        }
        setError(reason);
      })
      .finally(() => {
        if (!active) {
          return;
        }
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [...deps, reloadCount]);

  return {
    data,
    loading,
    error,
    reload: () => setReloadCount((value) => value + 1),
    setData,
    setError,
  };
}
