import type { Board } from "@repo/store";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { boardApi, type UpdateBoardInput } from "@/lib/api/board-api";
import { useAuthStore } from "@/stores/auth";

import { useSyncNotification } from "./use-sync-notification";

// Board-level signature only: the list toast should fire on board add/remove/
// rename, description, member and project add/remove — but NOT on nested
// project/task detail changes (those are detected after opening a board).
const boardSignature = (b: Board) => ({
  _id: b._id,
  title: b.title,
  description: b.description ?? null,
  owner: typeof b.owner === "string" ? b.owner : b.owner?._id,
  members: b.members.map((m) => m._id),
  projects: b.projects.map((p) => p._id)
});

export const boardListComparable = (data: { myBoards?: Board[]; teamBoards?: Board[] }) => ({
  my: (data.myBoards ?? []).map(boardSignature),
  team: (data.teamBoards ?? []).map(boardSignature)
});

export const BOARD_KEYS = {
  all: ["boards"] as const,
  lists: () => [...BOARD_KEYS.all, "list"] as const,
  list: () => [...BOARD_KEYS.lists()] as const,
  details: () => [...BOARD_KEYS.all, "detail"] as const,
  detail: (id: string) => [...BOARD_KEYS.details(), id] as const
};

export const useBoards = () => {
  // Only query once logged in — prevents unauthenticated 401 spam at app launch.
  const user = useAuthStore((state) => state.user);
  const query = useQuery({
    queryKey: BOARD_KEYS.list(),
    queryFn: async () => boardApi.getBoards(),
    enabled: !!user,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    // ponytail: 5s polling = near-real-time sync across users
    refetchInterval: 5000
  });

  useSyncNotification(query.data, BOARD_KEYS.list(), boardListComparable);

  return query;
};

export const useBoard = (boardId?: string) => {
  const user = useAuthStore((state) => state.user);
  const query = useQuery({
    queryKey: BOARD_KEYS.detail(boardId || ""),
    queryFn: async () => boardApi.getBoardById(boardId || ""),
    enabled: !!boardId && !!user,
    refetchInterval: 5000
  });

  useSyncNotification(query.data, BOARD_KEYS.detail(boardId || ""));

  return query;
};

export const useCreateBoard = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: boardApi.createBoard,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BOARD_KEYS.list() });
    }
  });
};

export const useUpdateBoard = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...updates }: { id: string } & UpdateBoardInput) =>
      boardApi.updateBoard(id, updates),
    onSuccess: (updatedBoard) => {
      queryClient.invalidateQueries({ queryKey: BOARD_KEYS.list() });
      queryClient.invalidateQueries({ queryKey: BOARD_KEYS.detail(updatedBoard._id) });
    }
  });
};

export const useDeleteBoard = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: boardApi.deleteBoard,
    onSuccess: (_, boardId) => {
      queryClient.invalidateQueries({ queryKey: BOARD_KEYS.list() });
      queryClient.removeQueries({ queryKey: BOARD_KEYS.detail(boardId) });
    }
  });
};
