import { useCallback, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import Toast from "react-native-toast-message";

import { shouldSkipAndClear } from "@/lib/sync-state";

const identity = <T>(d: T): unknown => d;

/**
 * Shows a toast when query data changes via polling.
 * No toast on initial load or when data is unchanged.
 *
 * `getComparable` narrows what counts as a change — e.g. the board list only
 * cares about board-level fields, not nested project/task detail. Pass a
 * stable (module-level) function so it doesn't change identity each render.
 */
export function useSyncNotification<T>(
  data: T | undefined,
  queryKey: readonly unknown[],
  getComparable: (data: T) => unknown = identity
) {
  const prevDataRef = useRef<string | null>(null);
  const isInitialRef = useRef(true);
  const { t } = useTranslation();

  const serializedQueryKey = JSON.stringify(queryKey);

  useEffect(() => {
    // Skip if no data yet
    if (data === undefined) {
      return;
    }

    const current = JSON.stringify(getComparable(data));

    // Skip initial load
    if (isInitialRef.current) {
      isInitialRef.current = false;
      prevDataRef.current = current;
      return;
    }

    // Skip if data unchanged
    if (current === prevDataRef.current) {
      return;
    }

    prevDataRef.current = current;

    // Skip if this key was marked to skip (local mutation)
    if (shouldSkipAndClear(serializedQueryKey)) {
      return;
    }

    // Show sync toast (debounced - only one at a time)
    Toast.show({
      type: "sync",
      text1: t("common.synced"),
      visibilityTime: 2000,
      autoHide: true,
      position: "bottom",
      bottomOffset: 100 // clears the bottom tab bar
    });
  }, [data, serializedQueryKey, t, getComparable]);

  const skipNext = useCallback(() => {
    // This is for external callers, but we'll use the module-level function instead
  }, []);

  return { skipNext };
}
