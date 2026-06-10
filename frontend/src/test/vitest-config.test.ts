import { describe, expect, test } from "vitest";

describe("Vitest setup", () => {
  test("test_vitest_config_loads", () => {
    expect(1).toBe(1);
    expect(document.body).toBeInTheDocument();
  });
});
