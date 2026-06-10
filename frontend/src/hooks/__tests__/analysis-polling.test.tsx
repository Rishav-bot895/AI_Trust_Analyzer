import { act, renderHook } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, test, vi } from "vitest";
import type { AnalysisResponse, AnalysisRequest } from "../../types/api";

const submitAnalysisMock = vi.fn();
const getAnalysisMock = vi.fn();

vi.mock("../../lib/api-client", () => ({
  submitAnalysis: (...args: unknown[]) => submitAnalysisMock(...args),
  getAnalysis: (...args: unknown[]) => getAnalysisMock(...args),
}));

vi.mock("../../lib/guest-session", () => ({
  initializeGuestSession: vi.fn(async () => null),
  getOrCreateGuestSessionId: vi.fn(() => null),
  registerGuestSessionLifecycle: vi.fn(() => () => undefined),
}));

import { useAnalysis } from "../useAnalysis";
import { usePolling } from "../usePolling";

const BASE_ANALYSIS: AnalysisResponse = {
  id: "analysis-1",
  status: "PENDING",
  trustScore: null,
  hallucinationRisk: null,
  claims: [],
  evidence: [],
  timeline: [],
  critique: null,
  verdict: null,
  createdAt: "2026-01-01T00:00:00Z",
  completedAt: null,
  error: null,
};

const REQUEST: AnalysisRequest = {
  prompt: "prompt",
  response: "response with enough detail for testing",
  userMode: "AUTHENTICATED",
};

async function flush() {
  await Promise.resolve();
  await Promise.resolve();
}

describe("Task 4.7 hooks", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    submitAnalysisMock.mockReset();
    getAnalysisMock.mockReset();
    window.sessionStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("test_use_analysis_submit_sets_loading", async () => {
    submitAnalysisMock.mockImplementation(
      () => new Promise<{ id: string }>(() => undefined),
    );

    const { result } = renderHook(() => useAnalysis());

    void act(() => {
      void result.current.submit(REQUEST);
    });

    expect(result.current.phase).toBe("submitting");
  });

  test("test_use_polling_stops_on_completed", async () => {
    getAnalysisMock.mockResolvedValue({
      ...BASE_ANALYSIS,
      status: "COMPLETED",
      trustScore: 84,
      completedAt: "2026-01-01T00:00:02Z",
    } satisfies AnalysisResponse);

    const { result } = renderHook(() => usePolling("analysis-1", 100));

    act(() => {
      result.current.startPolling();
    });

    await act(async () => {
      vi.advanceTimersByTime(110);
      await flush();
    });

    expect(result.current.status).toBe("COMPLETED");
    expect(result.current.isPolling).toBe(false);
    expect(getAnalysisMock).toHaveBeenCalledTimes(1);
  });

  test("test_use_polling_cleans_up_on_unmount", async () => {
    getAnalysisMock.mockResolvedValue({
      ...BASE_ANALYSIS,
      status: "PENDING",
    } satisfies AnalysisResponse);

    const { result, unmount } = renderHook(() => usePolling("analysis-1", 100));

    act(() => {
      result.current.startPolling();
    });

    await act(async () => {
      vi.advanceTimersByTime(110);
      await flush();
    });

    expect(getAnalysisMock).toHaveBeenCalledTimes(1);

    unmount();

    await act(async () => {
      vi.advanceTimersByTime(400);
      await flush();
    });

    expect(getAnalysisMock).toHaveBeenCalledTimes(1);
  });

  test("test_use_analysis_sets_error_on_failure", async () => {
    submitAnalysisMock.mockRejectedValue(new Error("submission exploded"));

    const { result } = renderHook(() => useAnalysis());

    await act(async () => {
      await result.current.submit(REQUEST);
      await flush();
    });

    expect(result.current.phase).toBe("error");
    expect(result.current.error).toContain("submission exploded");
  });
});
