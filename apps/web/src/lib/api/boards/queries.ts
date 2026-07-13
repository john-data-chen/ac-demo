import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { markSkipNext } from "@/lib/hooks/sync-state";
import { useWorkspaceStore } from "@/stores/workspace-store";
import { BOARD_KEYS } from "@/types/boardApi";

import { boardApi } from "../boardApi";

export const useBoards = () => {
  // Only query once logged in — userId is set after session is confirmed.
  // Prevents unauthenticated 401 spam from the always-mounted sidebar.
  const userId = useWorkspaceStore((state) => state.userId);
  return useQuery({
    queryKey: BOARD_KEYS.list(),
    queryFn: async () => {
      return boardApi.getBoards();
    },
    enabled: !!userId,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
    // ponytail: 5s polling = near-real-time sync across users
    refetchInterval: 5000
  });
};

export const useBoard = (boardId?: string) => {
  const userId = useWorkspaceStore((state) => state.userId);
  return useQuery({
    queryKey: BOARD_KEYS.detail(boardId || ""),
    queryFn: async () => boardApi.getBoardById(boardId || ""),
    enabled: !!boardId && !!userId,
    refetchInterval: 5000
  });
};

export const useCreateBoard = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: Parameters<typeof boardApi.createBoard>[0]) =>
      boardApi.createBoard(input),
    onMutate: () => {
      markSkipNext("boards");
    },
    onSuccess: () => {
      // Invalidate the boards list query to refetch
      queryClient
        .invalidateQueries({
          queryKey: BOARD_KEYS.list()
        })
        .catch(() => {});
    }
  });
};

export const useUpdateBoard = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      ...updates
    }: { id: string } & Parameters<typeof boardApi.updateBoard>[1]) =>
      boardApi.updateBoard(id, updates),
    onMutate: () => {
      markSkipNext("boards");
    },
    onSuccess: (updatedBoard) => {
      // Invalidate both the list and the specific board
      queryClient.invalidateQueries({ queryKey: BOARD_KEYS.list() }).catch(() => {});
      queryClient
        .invalidateQueries({ queryKey: BOARD_KEYS.detail(updatedBoard._id) })
        .catch(() => {});
    }
  });
};

export const useDeleteBoard = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => boardApi.deleteBoard(id),
    onMutate: () => {
      markSkipNext("boards");
    },
    onSuccess: (_, boardId) => {
      // Invalidate the boards list
      queryClient.invalidateQueries({ queryKey: BOARD_KEYS.list() }).catch(() => {});
      // Remove the specific board from the cache
      queryClient.removeQueries({
        queryKey: BOARD_KEYS.detail(boardId)
      });
    }
  });
};

export const useAddBoardMember = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ boardId, memberId }: { boardId: string; memberId: string }) =>
      boardApi.addBoardMember(boardId, memberId),
    onSuccess: (updatedBoard) => {
      // Invalidate the board data
      queryClient
        .invalidateQueries({ queryKey: BOARD_KEYS.detail(updatedBoard._id) })
        .catch(() => {});
      queryClient.invalidateQueries({ queryKey: BOARD_KEYS.list() }).catch(() => {});
    }
  });
};
