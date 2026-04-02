import { DependencyList, useCallback, useEffect, useState } from "react";

export function useAsyncResource<T>(loader: () => Promise<T>, deps: DependencyList) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const value = await loader();
      setData(value);
    } catch (err) {
      const message =
        typeof err === "object" && err && "response" in err
          ? ((err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? "Request failed")
          : "Request failed";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, deps);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, isLoading, error, reload: load };
}
