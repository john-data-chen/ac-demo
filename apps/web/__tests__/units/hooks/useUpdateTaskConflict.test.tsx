import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useUpdateTask } from "@/lib/api/tasks/queries";
import { useWorkspaceStore } from "@/stores/workspace-store";
import { TASK_KEYS } from "@/types/taskApi";

vi.mock("@/lib/api/taskApi", () => ({
  taskApi: {
    getTasks: vi.fn(),
    getTaskById: vi.fn(),
    createTask: vi.fn(),
    updateTask: vi.fn(),
    deleteTask: vi.fn()
  }
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() }
}));

// Raw server-side isoformat string — must be passed through untouched
const serverUpdatedAt = "2026-07-08T10:00:00.123456+00:00";

const cachedTask = {
  _id: "t1",
  title: "Cached task",
  status: "TODO",
  project: "p1",
  board: "b1",
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
    useWorkspaceStore.setState({ userId: "u1" });
  });

  it("sends the cached updatedAt as the lock token", async () => {
    const { taskApi } = await import("@/lib/api/taskApi");
    vi.mocked(taskApi.updateTask).mockResolvedValue({ ...cachedTask, title: "New" } as never);

    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(TASK_KEYS.detail("t1"), cachedTask);

    const { result } = renderHook(() => useUpdateTask(), { wrapper });
    await result.current.mutateAsync({ id: "t1", title: "New" });

    expect(taskApi.updateTask).toHaveBeenCalledWith(
      "t1",
      expect.objectContaining({ title: "New", lastModifier: "u1", updatedAt: serverUpdatedAt })
    );
  });

  it("shows a conflict toast when the server responds 409", async () => {
    const { taskApi } = await import("@/lib/api/taskApi");
    const { toast } = await import("sonner");
    const conflict = Object.assign(new Error("Task was modified by someone else."), {
      status: 409
    });
    vi.mocked(taskApi.updateTask).mockRejectedValue(conflict);

    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(TASK_KEYS.detail("t1"), cachedTask);

    const { result } = renderHook(() => useUpdateTask(), { wrapper });
    await expect(result.current.mutateAsync({ id: "t1", title: "New" })).rejects.toThrow();

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled();
    });
  });

  it("skips the lock token on cache miss (opt-in behavior)", async () => {
    const { taskApi } = await import("@/lib/api/taskApi");
    vi.mocked(taskApi.updateTask).mockResolvedValue({ ...cachedTask, title: "New" } as never);

    const { wrapper } = makeWrapper(); // no cache seeded

    const { result } = renderHook(() => useUpdateTask(), { wrapper });
    await result.current.mutateAsync({ id: "t1", title: "New" });

    const sentBody = vi.mocked(taskApi.updateTask).mock.calls[0][1];
    expect(sentBody).not.toHaveProperty("updatedAt");
  });
});
