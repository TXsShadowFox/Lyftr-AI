import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, fetchHealth } from "../lib/api";
import type { HealthResponse } from "../types";

export type HealthState =
  | { status: "loading" }
  | { status: "ok"; data: HealthResponse }
  | {
      status: "degraded";
      keysConfigured?: number;
      cacheEnabled?: boolean;
      detail?: string;
    }
  | { status: "offline"; detail: string };

export function useHealth() {
  const [state, setState] = useState<HealthState>({ status: "loading" });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const mounted = useRef(true);

  const refresh = useCallback(async (silent: boolean) => {
    if (!silent) {
      setIsRefreshing(true);
    }

    try {
      const data = await fetchHealth();
      if (mounted.current) {
        setState({ status: "ok", data });
      }
    } catch (error) {
      if (!mounted.current) {
        return;
      }

      if (error instanceof ApiError && error.status === 503) {
        const body = (error.body ?? {}) as Partial<HealthResponse> & {
          detail?: string;
        };
        setState({
          status: "degraded",
          keysConfigured: body.keys_configured,
          cacheEnabled: body.cache_enabled,
          detail: body.detail,
        });
      } else {
        setState({
          status: "offline",
          detail: "API unreachable. Start the backend and refresh.",
        });
      }
    } finally {
      if (mounted.current && !silent) {
        setIsRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    void refresh(true);
    const timer = window.setInterval(() => void refresh(true), 60_000);
    return () => {
      mounted.current = false;
      window.clearInterval(timer);
    };
  }, [refresh]);

  return {
    state,
    isRefreshing,
    refresh: () => void refresh(false),
  };
}
