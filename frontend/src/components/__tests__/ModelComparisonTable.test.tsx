import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { ModelComparisonTable } from "../ModelComparisonTable";
import type { AnalysisResponse } from "../../types/api";

function createAnalysis(score: number | null, modelName: string | null = null): AnalysisResponse {
  return {
    id: `analysis-${score ?? "null"}`,
    status: "COMPLETED",
    prompt: "Prompt",
    response: "Response",
    modelName,
    trustScore: score,
    hallucinationRisk: score === null ? "UNKNOWN" : score >= 80 ? "LOW" : score >= 50 ? "MEDIUM" : "HIGH",
    claims: [
      {
        id: "claim-1",
        text: "Sample claim",
        confidence: 0.8,
        status: "SUPPORTED",
        claimIndex: 0,
        sourceSpan: null,
      },
      {
        id: "claim-2",
        text: "Sample contradiction",
        confidence: 0.7,
        status: "CONTRADICTED",
        claimIndex: 1,
        sourceSpan: null,
      },
      {
        id: "claim-3",
        text: "Sample unsupported",
        confidence: 0.5,
        status: "UNSUPPORTED",
        claimIndex: 2,
        sourceSpan: null,
      },
    ],
    evidence: [],
    timeline: [],
    critique: null,
    verdict: "Model verdict summary",
    createdAt: "2026-01-01T00:00:00Z",
    completedAt: "2026-01-01T00:00:01Z",
    error: null,
  };
}

describe("ModelComparisonTable", () => {
  test("test_comparison_highlights_best_model", () => {
    render(
      <ModelComparisonTable
        models={["Model Alpha", "Model Beta"]}
        analyses={[createAnalysis(72), createAnalysis(91)]}
      />,
    );

    expect(screen.getByText("Model Beta")).toBeInTheDocument();
    expect(screen.getByText("Best")).toBeInTheDocument();
  });

  test("test_comparison_prefers_response_model_name_from_analysis", () => {
    render(
      <ModelComparisonTable
        models={["Fallback"]}
        analyses={[createAnalysis(88, "claude-sonnet")]}
      />,
    );

    expect(screen.getByText("Claude Sonnet")).toBeInTheDocument();
  });

  test("test_comparison_shows_delta", () => {
    render(
      <ModelComparisonTable
        models={["Model Alpha", "Model Beta"]}
        analyses={[createAnalysis(70), createAnalysis(82)]}
      />,
    );

    expect(screen.getByText("(+12)")).toBeInTheDocument();
  });

  test("test_comparison_sort_by_score", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ModelComparisonTable
        models={["Model Alpha", "Model Beta", "Model Gamma"]}
        analyses={[createAnalysis(70), createAnalysis(82), createAnalysis(40)]}
      />,
    );

    const firstBodyRowText = () =>
      (container.querySelectorAll("tbody tr")[0]?.textContent ?? "").trim();

    expect(firstBodyRowText()).toContain("Model Beta");

    await user.click(screen.getByRole("button", { name: /Trust Score/i }));

    expect(firstBodyRowText()).toContain("Model Gamma");
  });

  test("test_comparison_empty_state", () => {
    render(<ModelComparisonTable models={[]} analyses={[]} />);

    expect(screen.getByText("Run a comparison to see results")).toBeInTheDocument();
  });
});
