import type { Task, UpdateTaskInput } from "@repo/store";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert } from "react-native";

import { taskApi } from "@/lib/api/task-api";
import { useAuthStore } from "@/stores/auth";

import { useSyncNotification } from "./use-sync-notification";

export const TASK_KEYS = {
  all: ["tasks"] as const,
  lists: () => [...TASK_KEYS.all, "list"] as const,
  list: (filters: { project?: string; assignee?: string } = {}) =>
    [
      ...TASK_KEYS.lists(),
      ...(filters.project ? [{ project: filters.project }] : []),
      ...(filters.assignee ? [{ assignee: filters.assignee }] : [])
    ] as const,
  details: () => [...TASK_KEYS.all, "detail"] as const,
  detail: (id: string) => [...TASK_KEYS.details(), id] as const
};

export const useTasks = (projectId?: string, assigneeId?: string) => {
  const query = useQuery({
    queryKey: TASK_KEYS.list({ project: projectId, assignee: assigneeId }),
    queryFn: async () => taskApi.getTasks(projectId, assigneeId),
    enabled: !!projectId || !!assigneeId,
    staleTime: 0,
    gcTime: 5 * 60 * 1000,
    // ponytail: 5s polling = near-real-time sync; RN has no window focus, so
    // this is also what refreshes the list when returning to the screen
    refetchInterval: 5000
  });

  useSyncNotification(query.data, TASK_KEYS.list({ project: projectId, assignee: assigneeId }));

  return query;
};

export const useTask = (taskId?: string) => {
  return useQuery({
    queryKey: TASK_KEYS.detail(taskId || ""),
    queryFn: async () => taskApi.getTaskById(taskId || ""),
    enabled: !!taskId
  });
};

export const useCreateTask = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: taskApi.createTask,
    onSuccess: (newTask) => {
      queryClient
        .invalidateQueries({ queryKey: TASK_KEYS.list({ project: newTask.project }) })
        .catch(() => {});
      if (newTask.assignee) {
        const assigneeId =
          typeof newTask.assignee === "string" ? newTask.assignee : newTask.assignee._id;
        queryClient
          .invalidateQueries({ queryKey: TASK_KEYS.list({ assignee: assigneeId }) })
          .catch(() => {});
      }
    }
  });
};

export const useUpdateTask = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  return useMutation({
    mutationFn: async ({
      id,
      ...updates
    }: { id: string } & Omit<UpdateTaskInput, "lastModifier">) => {
      if (!user?._id) {
        throw new Error("User must be authenticated");
      }
      // Optimistic lock: send the updatedAt we last saw so the server can
      // 409 if someone else changed the task meanwhile. Cache miss = lock
      // skipped (server treats it as opt-in).
      const cachedTask =
        queryClient.getQueryData<Task>(TASK_KEYS.detail(id)) ??
        queryClient
          .getQueriesData<Task[]>({ queryKey: TASK_KEYS.lists() })
          .flatMap(([, tasks]) => tasks ?? [])
          .find((task) => task._id === id);
      // Pass the server's string through untouched: JS toISOString() formats
      // differently from Python isoformat() and would false-409.
      const lockToken = cachedTask?.updatedAt;
      return taskApi.updateTask(id, {
        ...updates,
        lastModifier: user._id,
        ...(typeof lockToken === "string" ? { updatedAt: lockToken } : {})
      });
    },
    onSuccess: (updatedTask) => {
      queryClient
        .invalidateQueries({ queryKey: TASK_KEYS.detail(updatedTask._id) })
        .catch(() => {});
      queryClient
        .invalidateQueries({ queryKey: TASK_KEYS.list({ project: updatedTask.project }) })
        .catch(() => {});
    },
    onError: (err) => {
      if ((err as Error & { status?: number }).status === 409) {
        Alert.alert(
          "Task changed",
          "Someone else just updated this task. Showing the latest version."
        );
        queryClient.invalidateQueries({ queryKey: TASK_KEYS.all }).catch(() => {});
      }
    }
  });
};

export const useDeleteTask = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: taskApi.deleteTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TASK_KEYS.lists() }).catch(() => {});
    }
  });
};

export const useMoveTask = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      taskId,
      projectId,
      orderInProject
    }: {
      taskId: string;
      projectId: string;
      orderInProject: number;
    }) => taskApi.moveTask(taskId, projectId, orderInProject),
    onSuccess: (updatedTask) => {
      queryClient.invalidateQueries({ queryKey: TASK_KEYS.lists() }).catch(() => {});
      queryClient
        .invalidateQueries({ queryKey: TASK_KEYS.detail(updatedTask._id) })
        .catch(() => {});
    }
  });
};
