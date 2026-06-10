import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { ResultsView } from "../ResultsView";
import type { AnalysisListItem, AnalysisResponse, ComparisonResponse } from "../../types/api";

vi.mock("@xyflow/react", () => ({
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="react-flow-provider">{children}</div>
  ),
  ReactFlow: ({
    nodes,
    children,
  }: {
    nodes: Array<{ id: string; data?: { label?: React.ReactNode } }>;
    children?: React.ReactNode;
  }) => (
    <div data-testid="react-flow-canvas">
      {nodes.map((node) => (
        <div key={node.id}>{node.data?.label}</div>
      ))}
      {children}
    </div>
  ),
  Background: () => null,
}));

const analysisFixture: AnalysisResponse = {
  id: "analysis-1",
  status: "COMPLETED",
  trustScore: 86,
  hallucinationRisk: "LOW",
  claims: [
    {
      id: "claim-1",
      text: "Apollo 11 landed on the Moon in 1969.",
      confidence: 0.94,
      status: "SUPPORTED",
      claimIndex: 0,
      sourceSpan: null,
    },
  ],
  evidence: [
    {
      id: "evidence-1",
      claimId: "claim-1",
      snippet: "NASA states Apollo 11 landed in July 1969.",
      sourceUrl: "https://example.com/apollo",
      sourceTitle: "Apollo source",
      relevanceScore: 0.96,
      sourceType: "WEB_SEARCH",
      polarity: "FOR",
      retrievedAt: "2026-01-01T00:00:00Z",
    },
  ],
  timeline: [
    {
      agent: "claim_extractor",
      startedAt: "2026-01-01T00:00:00Z",
      completedAt: "2026-01-01T00:00:01Z",
      inputSummary: "response text",
      outputSummary: "1 claim extracted",
    },
  ],
  critique: "## Logical Issues\n\nNo logical issues detected.",
  verdict: "The response is well supported.",
  createdAt: "2026-01-01T00:00:00Z",
  completedAt: "2026-01-01T00:00:02Z",
  error: null,
};

const comparisonFixture: ComparisonResponse = {
  analyses: [
    analysisFixture,
    {
      ...analysisFixture,
      id: "analysis-2",
      trustScore: 72,
      hallucinationRisk: "MEDIUM",
      verdict: "Mostly supported with caveats.",
    },
  ],
};

const historyFixture: AnalysisListItem[] = [
  {
    id: "history-1",
    status: "COMPLETED",
    trustScore: 80,
    hallucinationRisk: "LOW",
    createdAt: "2026-01-02T10:00:00Z",
    completedAt: "2026-01-02T10:00:02Z",
    error: null,
  },
];

describe("ResultsView", () => {
  test("test_results_view_renders_score_card", () => {
    render(<ResultsView analysis={analysisFixture} />);

    expect(screen.getByText("LOW RISK")).toBeInTheDocument();
    expect(screen.getByText("86")).toBeInTheDocument();
    expect(screen.getByText("The response is well supported.")).toBeInTheDocument();
  });

  test("test_results_view_renders_all_tabs", async () => {
    const user = userEvent.setup();
    window.history.replaceState(null, "", "#claims");

    render(
      <ResultsView
        analysis={analysisFixture}
        comparison={comparisonFixture}
        comparisonModels={["Model A", "Model B"]}
        showHistoryTab
        history={historyFixture}
      />,
    );

    expect(screen.getByRole("tab", { name: /Claims/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Evidence/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Timeline/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Compare/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /History/i })).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /Evidence/i }));
    expect(screen.getByText("NASA states Apollo 11 landed in July 1969.")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /Timeline/i }));
    expect(screen.getByText("Extractor")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /Compare/i }));
    expect(screen.getByText("Model A")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /History/i }));
    expect(screen.getByText("Claim Summary")).toBeInTheDocument();
    expect(screen.getByText("Previous Analyses")).toBeInTheDocument();
  });

  test("test_results_view_loading_shows_skeleton", () => {
    render(<ResultsView analysis={{ ...analysisFixture, status: "RUNNING", trustScore: null }} />);

    expect(screen.getByLabelText("results-loading-skeleton")).toBeInTheDocument();
  });

  test("test_critique_markdown_renders_headings", () => {
    render(<ResultsView analysis={analysisFixture} />);

    expect(
      screen.getByRole("heading", { level: 2, name: "Logical Issues" }),
    ).toBeInTheDocument();
    expect(screen.getByText("No logical issues detected.")).toBeInTheDocument();
  });
});
