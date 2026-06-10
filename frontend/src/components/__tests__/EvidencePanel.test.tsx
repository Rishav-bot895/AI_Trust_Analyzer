import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { EvidencePanel } from "../EvidencePanel";
import type { Evidence } from "../../types/api";

const claimsFixture = [
  {
    id: "claim-1",
    text: "The Eiffel Tower is in Paris.",
    claimIndex: 0,
  },
  {
    id: "claim-2",
    text: "The moon is made of cheese.",
    claimIndex: 1,
  },
];

const evidenceFixture: Evidence[] = [
  {
    id: "ev-1",
    claimId: "claim-1",
    snippet: "Paris is the capital city of France.",
    sourceUrl: "https://example.com/paris",
    sourceTitle: "Paris source",
    relevanceScore: 0.91,
    sourceType: "WEB_SEARCH",
    polarity: "FOR",
    retrievedAt: "2026-01-01T00:00:00Z",
  },
  {
    id: "ev-2",
    claimId: "claim-2",
    snippet: "No credible source supports this statement.",
    sourceUrl: "https://example.com/moon",
    sourceTitle: "Moon source",
    relevanceScore: 0.62,
    sourceType: "PGVECTOR",
    polarity: "AGAINST",
    retrievedAt: "2026-01-01T00:00:00Z",
  },
];

describe("EvidencePanel", () => {
  test("test_evidence_grouped_by_claim", () => {
    render(<EvidencePanel evidence={evidenceFixture} claims={claimsFixture} />);

    expect(screen.getAllByText("Claim 1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Claim 2").length).toBeGreaterThan(0);
    expect(screen.getByText("The Eiffel Tower is in Paris.")).toBeInTheDocument();
    expect(screen.getByText("The moon is made of cheese.")).toBeInTheDocument();
    expect(screen.getByText(/Paris is the capital city of France\./)).toBeInTheDocument();
    expect(screen.getByText(/No credible source supports this statement\./)).toBeInTheDocument();
  });

  test("test_evidence_filter_tabs_show_selected_claim", async () => {
    const user = userEvent.setup();
    render(<EvidencePanel evidence={evidenceFixture} claims={claimsFixture} />);

    expect(screen.getByRole("button", { name: "All Claims" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Claim 2" }));

    expect(screen.getByText("The moon is made of cheese.")).toBeInTheDocument();
    expect(screen.getByText(/No credible source supports this statement\./)).toBeInTheDocument();
    expect(screen.queryByText("The Eiffel Tower is in Paris.")).not.toBeInTheDocument();
    expect(screen.queryByText(/Paris is the capital city of France\./)).not.toBeInTheDocument();
  });

  test("test_evidence_badges_show_source_polarity_and_relevance", () => {
    render(<EvidencePanel evidence={evidenceFixture} claims={claimsFixture} />);

    expect(screen.getByText("WEB")).toBeInTheDocument();
    expect(screen.getByText("VECTOR")).toBeInTheDocument();
    expect(screen.getByText("Supports")).toBeInTheDocument();
    expect(screen.getByText("Contradicts")).toBeInTheDocument();
    expect(screen.getByText("Relevance 91%")).toBeInTheDocument();
    expect(screen.getByText("Relevance 62%")).toBeInTheDocument();
  });

  test("test_evidence_url_opens_new_tab", () => {
    render(<EvidencePanel evidence={evidenceFixture} claims={claimsFixture} />);

    const link = screen.getByRole("link", { name: "Paris source" });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  test("test_evidence_show_more_expands", async () => {
    const user = userEvent.setup();
    const longSnippet = "A".repeat(220);
    const truncatedSnippet = `"${"A".repeat(200)}..."`;

    render(
      <EvidencePanel
        claims={[claimsFixture[0]]}
        evidence={[
          {
            ...evidenceFixture[0],
            id: "ev-long",
            claimId: "claim-1",
            snippet: longSnippet,
            sourceUrl: "https://example.com/long",
            sourceTitle: "Long snippet source",
          },
        ]}
      />,
    );

    expect(screen.getByText(truncatedSnippet)).toBeInTheDocument();
    expect(screen.queryByText(`"${longSnippet}"`)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Show more" }));

    expect(screen.getByText(`"${longSnippet}"`)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Show less" }));

    expect(screen.getByText(truncatedSnippet)).toBeInTheDocument();
    expect(screen.queryByText(`"${longSnippet}"`)).not.toBeInTheDocument();
  });

  test("test_evidence_null_url_not_rendered", () => {
    render(
      <EvidencePanel
        claims={[claimsFixture[0]]}
        evidence={[
          {
            ...evidenceFixture[0],
            id: "ev-null-url",
            claimId: "claim-1",
            sourceUrl: null,
            sourceTitle: null,
          },
        ]}
      />,
    );

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  test("test_evidence_empty_state_message", () => {
    render(<EvidencePanel evidence={[]} claims={claimsFixture} />);

    expect(screen.getByText("No evidence retrieved")).toBeInTheDocument();
  });

  test("test_evidence_claim_without_entries_shows_empty_group", () => {
    render(<EvidencePanel evidence={[evidenceFixture[0]]} claims={claimsFixture} />);

    expect(screen.getByText("The moon is made of cheese.")).toBeInTheDocument();
    expect(screen.getByText("No evidence retrieved")).toBeInTheDocument();
  });

  test("test_evidence_panel_shows_skeleton_cards", () => {
    render(<EvidencePanel evidence={[]} claims={claimsFixture} isLoading />);

    expect(screen.getByLabelText("evidence-panel-skeleton")).toBeInTheDocument();
    expect(screen.getAllByLabelText("evidence-card-skeleton")).toHaveLength(2);
    expect(screen.queryByText("No evidence retrieved")).not.toBeInTheDocument();
  });
});
