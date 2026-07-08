import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { boardApi, type UpdateBoardInput } from "@/lib/api/board-api";

import { useSyncNotification } from "./use-sync-notification";

export const BOARD_KEYS = {
  all: ["boards"] as const,
  lists: () => [...BOARD_KEYS.all, "list"] as const,
  list: () => [...BOARD_KEYS.lists()] as const,
  details: () => [...BOARD_KEYS.all, "detail"] as const,
  detail: (id: string) => [...BOARD_KEYS.details(), id] as const
};

export const useBoards = () => {
  const query = useQuery({
    queryKey: BOARD_KEYS.list(),
    queryFn: async () => boardApi.getBoards(),
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    // ponytail: 5s polling = near-real-time sync across users
    refetchInterval: 5000
  });

  useSyncNotification(query.data, BOARD_KEYS.list());

  return query;
};

export const useBoard = (boardId?: string) => {
  const query = useQuery({
    queryKey: BOARD_KEYS.detail(boardId || ""),
    queryFn: async () => boardApi.getBoardById(boardId || ""),
    enabled: !!boardId,
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
