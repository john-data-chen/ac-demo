import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { Alert } from "react-native";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TASK_KEYS, useUpdateTask } from "@/hooks/use-tasks";
import { taskApi } from "@/lib/api/task-api";

vi.mock("@/lib/api/task-api", () => ({
  taskApi: {
    getTasks: vi.fn(),
    getTaskById: vi.fn(),
    createTask: vi.fn(),
    updateTask: vi.fn(),
    deleteTask: vi.fn(),
    moveTask: vi.fn(),
    getTaskPermissions: vi.fn()
  }
}));

vi.mock("@/stores/auth", () => ({
  useAuthStore: () => ({ user: { _id: "u1" } })
}));

// Raw server-side isoformat string — must be passed through untouched
const serverUpdatedAt = "2026-07-08T10:00:00.123456+00:00";

const cachedTask = {
  _id: "t1",
  title: "Cached task",
  status: "TODO",
  project: "p1",
  updatedAt: serverUpdatedAt
};

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

describe("useUpdateTask optimistic locking", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends the cached updatedAt as the lock token (from list cache)", async () => {
    vi.mocked(taskApi.updateTask).mockResolvedValue({ ...cachedTask, title: "New" } as never);

    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(TASK_KEYS.list({ project: "p1" }), [cachedTask]);

    const { result } = renderHook(() => useUpdateTask(), { wrapper });
    await result.current.mutateAsync({ id: "t1", title: "New" });

    expect(taskApi.updateTask).toHaveBeenCalledWith(
      "t1",
      expect.objectContaining({ title: "New", lastModifier: "u1", updatedAt: serverUpdatedAt })
    );
  });

  it("alerts and refetches on 409 conflict", async () => {
    const alertSpy = vi.spyOn(Alert, "alert").mockImplementation(() => {});
    const conflict = Object.assign(new Error("Task was modified by someone else."), {
      status: 409
    });
    vi.mocked(taskApi.updateTask).mockRejectedValue(conflict);

    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(TASK_KEYS.list({ project: "p1" }), [cachedTask]);
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useUpdateTask(), { wrapper });
    await expect(result.current.mutateAsync({ id: "t1", title: "New" })).rejects.toThrow();

    expect(alertSpy).toHaveBeenCalled();
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: TASK_KEYS.all });
  });

  it("skips the lock token on cache miss (opt-in behavior)", async () => {
    vi.mocked(taskApi.updateTask).mockResolvedValue({ ...cachedTask, title: "New" } as never);

    const { wrapper } = makeWrapper(); // no cache seeded

    const { result } = renderHook(() => useUpdateTask(), { wrapper });
    await result.current.mutateAsync({ id: "t1", title: "New" });

    const sentBody = vi.mocked(taskApi.updateTask).mock.calls[0][1];
    expect(sentBody).not.toHaveProperty("updatedAt");
  });
});
