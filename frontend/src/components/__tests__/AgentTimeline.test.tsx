import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { AgentTimeline } from "../AgentTimeline";
import type { TimelineEvent } from "../../types/api";

vi.mock("@xyflow/react", () => ({
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="react-flow-provider">{children}</div>
  ),
  ReactFlow: ({
    nodes,
    edges,
    children,
  }: {
    nodes: Array<{ id: string; data?: { label?: React.ReactNode } }>;
    edges: Array<{ id: string }>;
    children?: React.ReactNode;
  }) => (
    <div data-testid="react-flow-canvas">
      <span>{`edges:${edges.length}`}</span>
      {nodes.map((node) => (
        <div key={node.id}>{node.data?.label}</div>
      ))}
      {children}
    </div>
  ),
  Background: () => null,
}));

function extractorEvent(): TimelineEvent {
  return {
    agent: "claim_extractor",
    startedAt: "2026-06-10T10:00:00.000Z",
    completedAt: "2026-06-10T10:00:01.500Z",
    inputSummary: "response text",
    outputSummary: "claims extracted",
  };
}

describe("AgentTimeline", () => {
  test("test_timeline_renders_five_nodes", () => {
    render(<AgentTimeline timeline={[extractorEvent()]} />);

    expect(screen.getAllByText("Extractor").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Retriever").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Verifier").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Critic").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Judge").length).toBeGreaterThan(0);
    expect(screen.getByText("edges:4")).toBeInTheDocument();
  });

  test("test_timeline_empty_state", () => {
    render(<AgentTimeline timeline={[]} />);

    expect(screen.getByText("Timeline data not available for this analysis.")).toBeInTheDocument();
  });

  test("test_timeline_completed_node_shows_duration", () => {
    render(<AgentTimeline timeline={[extractorEvent()]} />);

    expect(screen.getAllByText("1.5s").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Extractor status")).toHaveTextContent("OK");
  });
});
