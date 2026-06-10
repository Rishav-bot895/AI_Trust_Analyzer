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

describe("AgentTimeline", () => {
  test("test_timeline_renders_five_nodes", () => {
    const timeline: TimelineEvent[] = [];

    render(<AgentTimeline timeline={timeline} />);

    expect(screen.getByText("Extractor")).toBeInTheDocument();
    expect(screen.getByText("Retriever")).toBeInTheDocument();
    expect(screen.getByText("Verifier")).toBeInTheDocument();
    expect(screen.getByText("Critic")).toBeInTheDocument();
    expect(screen.getByText("Judge")).toBeInTheDocument();
    expect(screen.getByText("edges:4")).toBeInTheDocument();
  });

  test("test_timeline_pending_shows_waiting", () => {
    render(<AgentTimeline timeline={[]} />);

    expect(screen.getAllByText("waiting").length).toBe(5);
  });

  test("test_timeline_completed_node_shows_duration", () => {
    const timeline: TimelineEvent[] = [
      {
        agent: "claim_extractor",
        startedAt: "2026-06-10T10:00:00.000Z",
        completedAt: "2026-06-10T10:00:01.500Z",
        inputSummary: "response text",
        outputSummary: "claims extracted",
      },
    ];

    render(<AgentTimeline timeline={timeline} />);

    expect(screen.getByText("1.5s")).toBeInTheDocument();
    expect(screen.getByLabelText("Extractor status")).toHaveTextContent("✓");
  });
});
