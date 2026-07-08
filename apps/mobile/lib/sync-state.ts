/**
 * Module-level sync state manager for mobile.
 * Tracks which query keys should skip the next sync notification.
 * Used to prevent showing "synced" toast when the change originated from this client.
 */

const skipKeys = new Set<string>();

export function markSkipNext(key: string) {
  skipKeys.add(key);
}

export function shouldSkipAndClear(key: string): boolean {
  if (skipKeys.has(key)) {
    skipKeys.delete(key);
    return true;
  }
  return false;
}
