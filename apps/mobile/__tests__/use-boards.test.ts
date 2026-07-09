import { renderHook, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  useBoards,
  useBoard,
  useCreateBoard,
  useUpdateBoard,
  useDeleteBoard,
  boardListComparable
} from "@/hooks/use-boards";
import { boardApi } from "@/lib/api/board-api";
import { useAuthStore } from "@/stores/auth";

import { Wrapper } from "./test-utils";

const login = () => {
  useAuthStore.getState().setUser({ _id: "u1", email: "a@b.c", name: "A" });
};

vi.mock("@/lib/api/board-api", () => ({
  boardApi: {
    getBoards: vi.fn(),
    getBoardById: vi.fn(),
    createBoard: vi.fn(),
    updateBoard: vi.fn(),
    deleteBoard: vi.fn()
  }
}));

describe("useBoards", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    login();
  });

  it("should fetch boards", async () => {
    const mockBoards = [{ _id: "b1", title: "Board 1" }];
    vi.mocked(boardApi.getBoards).mockResolvedValue(mockBoards as any);

    const { result } = renderHook(() => useBoards(), { wrapper: Wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockBoards);
    expect(boardApi.getBoards).toHaveBeenCalled();
  });

  it("should not fetch when logged out", () => {
    useAuthStore.getState().setUser(null);
    const { result } = renderHook(() => useBoards(), { wrapper: Wrapper });

    expect(result.current.fetchStatus).toBe("idle");
    expect(boardApi.getBoards).not.toHaveBeenCalled();
  });
});

describe("boardListComparable", () => {
  const makeBoard = (over: Record<string, unknown> = {}) =>
    ({
      _id: "b1",
      title: "Board 1",
      description: "d",
      owner: { _id: "u1", name: "A", email: "a@b.c" },
      members: [{ _id: "u1", name: "A", email: "a@b.c" }],
      projects: [{ _id: "p1", title: "Proj 1", tasks: [] }],
      ...over
    }) as any;

  const sig = (b: any) => JSON.stringify(boardListComparable({ myBoards: [b], teamBoards: [] }));

  it("ignores nested project title changes", () => {
    const a = makeBoard();
    const b = makeBoard({ projects: [{ _id: "p1", title: "Renamed", tasks: [{ _id: "t1" }] }] });
    expect(sig(a)).toBe(sig(b));
  });

  it("reflects project add/remove and board-level field changes", () => {
    const base = makeBoard();
    expect(sig(base)).not.toBe(sig(makeBoard({ title: "Changed" })));
    expect(sig(base)).not.toBe(sig(makeBoard({ projects: [{ _id: "p1" }, { _id: "p2" }] })));
    expect(sig(base)).not.toBe(sig(makeBoard({ members: [] })));
  });
});

describe("useBoard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    login();
  });

  it("should fetch a single board by id", async () => {
    const mockBoard = { _id: "b1", title: "Board 1" };
    vi.mocked(boardApi.getBoardById).mockResolvedValue(mockBoard as any);

    const { result } = renderHook(() => useBoard("b1"), { wrapper: Wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockBoard);
  });

  it("should not fetch when boardId is undefined", () => {
    const { result } = renderHook(() => useBoard(undefined), { wrapper: Wrapper });

    expect(result.current.fetchStatus).toBe("idle");
    expect(boardApi.getBoardById).not.toHaveBeenCalled();
  });
});

describe("useCreateBoard", () => {
  it("should call boardApi.createBoard", async () => {
    const newBoard = { _id: "b2", title: "New Board" };
    vi.mocked(boardApi.createBoard).mockResolvedValue(newBoard as any);

    const { result } = renderHook(() => useCreateBoard(), { wrapper: Wrapper });

    await act(async () => {
      result.current.mutate({ title: "New Board" });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(boardApi.createBoard).toHaveBeenCalledWith({ title: "New Board" }, expect.anything());
  });
});

describe("useUpdateBoard", () => {
  it("should call boardApi.updateBoard with id and updates", async () => {
    const updated = { _id: "b1", title: "Updated" };
    vi.mocked(boardApi.updateBoard).mockResolvedValue(updated as any);

    const { result } = renderHook(() => useUpdateBoard(), { wrapper: Wrapper });

    await act(async () => {
      result.current.mutate({ id: "b1", title: "Updated" });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(boardApi.updateBoard).toHaveBeenCalledWith("b1", { title: "Updated" });
  });
});

describe("useDeleteBoard", () => {
  it("should call boardApi.deleteBoard", async () => {
    vi.mocked(boardApi.deleteBoard).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteBoard(), { wrapper: Wrapper });

    await act(async () => {
      result.current.mutate("b1");
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(boardApi.deleteBoard).toHaveBeenCalledWith("b1", expect.anything());
  });
});
