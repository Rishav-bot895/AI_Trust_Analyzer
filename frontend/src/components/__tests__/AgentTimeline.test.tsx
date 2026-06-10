import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { AgentTimeline } from "../AgentTimeline";
import type { TimelineEvent } from "../../types/api";

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
  test("test_timeline_renders_five_agents", () => {
    render(<AgentTimeline timeline={[extractorEvent()]} />);

    expect(screen.getAllByText("Extractor").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Retriever").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Verifier").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Critic").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Judge").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("agent-timeline-flow")).toBeInTheDocument();
  });

  test("test_timeline_empty_state", () => {
    render(<AgentTimeline timeline={[]} />);

    expect(screen.getByText("Timeline data not available for this analysis.")).toBeInTheDocument();
  });

  test("test_timeline_completed_node_shows_duration_and_status", () => {
    render(<AgentTimeline timeline={[extractorEvent()]} />);

    expect(screen.getAllByText("1.5s").length).toBeGreaterThan(0);
    expect(screen.getByText("Done")).toBeInTheDocument();
    expect(screen.getByLabelText("Extractor status")).toHaveTextContent("1");
  });
});
