import { useEffect, useState } from 'preact/hooks';

export type FetchState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  refresh: () => void;
};

export async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status} for ${url}`);
  }

  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.toLowerCase().includes('application/json')) {
    const body = await response.text();
    throw new Error(`Expected JSON from ${url}, got ${contentType || 'unknown content type'}: ${body.slice(0, 120)}`);
  }

  return (await response.json()) as T;
}

export function useJsonResource<T>(factory: () => string | null, deps: unknown[] = []): FetchState<T> {
  const [nonce, setNonce] = useState(0);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const url = factory();
    if (!url) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchJson<T>(url)
      .then((payload) => {
        if (!cancelled) {
          setData(payload);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [nonce, ...deps]);

  return {
    data,
    error,
    loading,
    refresh: () => setNonce((value) => value + 1),
  };
}
