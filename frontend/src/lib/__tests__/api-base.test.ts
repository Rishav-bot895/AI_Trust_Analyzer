import { afterEach, describe, expect, test, vi } from "vitest";

describe("getApiBaseUrl", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  test("uses same-origin API proxy in production browsers", async () => {
    vi.stubGlobal("window", {
      location: {
        hostname: "aitrustanalyszer.vercel.app",
      },
    });

    const { getApiBaseUrl } = await import("../api-base");

    expect(getApiBaseUrl()).toBe("");
  });
});
