import { useTranslations } from "next-intl";
import { useCallback, useRef } from "react";
import { toast } from "sonner";

import { shouldSkipAndClear } from "./sync-state";

/**
 * Returns a function that shows a toast when data changes.
 * Use with manual polling (setInterval) - call compareAndNotify with new data.
 */
export function useSyncNotification() {
  const prevDataRef = useRef<Map<string, string>>(new Map());
  const t = useTranslations("common");
  const tRef = useRef(t);
  tRef.current = t;

  const compareAndNotify = useCallback((key: string, data: unknown) => {
    const current = JSON.stringify(data);
    const prev = prevDataRef.current.get(key);

    // Skip if data unchanged
    if (current === prev) {
      return;
    }

    prevDataRef.current.set(key, current);

    // Skip initial load (no previous data)
    if (prev === undefined) {
      return;
    }

    // Skip if this key was marked to skip (local mutation)
    if (shouldSkipAndClear(key)) {
      return;
    }

    // Show sync toast
    toast.success(tRef.current("synced"), {
      duration: 2000,
      position: "bottom-right"
    });
  }, []);

  return { compareAndNotify };
}
