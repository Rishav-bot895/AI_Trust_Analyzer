import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { TrustScoreCard } from "../TrustScoreCard";

describe("TrustScoreCard", () => {
  test("test_trust_score_high_renders_green", () => {
    render(
      <TrustScoreCard
        trustScore={85}
        hallucinationRisk="LOW"
        verdict="Strong evidence support across most claims."
      />,
    );

    expect(screen.getByText("LOW RISK")).toBeInTheDocument();
    expect(screen.getByText("85")).toBeInTheDocument();
  });

  test("test_trust_score_low_renders_red", () => {
    render(
      <TrustScoreCard
        trustScore={40}
        hallucinationRisk="HIGH"
        verdict="Several claims are contradicted or unsupported."
      />,
    );

    expect(screen.getByText("HIGH RISK")).toBeInTheDocument();
    expect(screen.getByText("40")).toBeInTheDocument();
  });

  test("test_null_score_shows_skeleton", () => {
    render(
      <TrustScoreCard
        trustScore={null}
        hallucinationRisk={null}
        verdict={null}
      />,
    );

    expect(screen.getByLabelText("trust-score-skeleton")).toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  test("test_trust_score_card_shows_skeleton_when_null", () => {
    render(
      <TrustScoreCard
        trustScore={null}
        hallucinationRisk={null}
        verdict={null}
      />,
    );

    expect(screen.getByLabelText("trust-score-card-skeleton")).toBeInTheDocument();
    expect(screen.getAllByTestId("skeleton").length).toBeGreaterThan(3);
  });

  test("test_verdict_text_displayed", () => {
    const verdict = "The response is mostly trustworthy with a few caveats.";

    render(
      <TrustScoreCard
        trustScore={72}
        hallucinationRisk="MEDIUM"
        verdict={verdict}
      />,
    );

    expect(screen.getByText("Verdict")).toBeInTheDocument();
    expect(screen.getByText(verdict)).toBeInTheDocument();
  });

  test("test_medium_score_renders_review_summary", () => {
    render(
      <TrustScoreCard
        trustScore={72}
        hallucinationRisk="MEDIUM"
        verdict="Mostly supported."
      />,
    );

    expect(screen.getByText("MEDIUM RISK")).toBeInTheDocument();
    expect(
      screen.getByText("Some claims may be uncertain or only partially supported. Review flagged items."),
    ).toBeInTheDocument();
  });

  test("test_score_is_clamped_to_display_range", () => {
    render(
      <TrustScoreCard
        trustScore={140}
        hallucinationRisk="LOW"
        verdict="Strong result."
      />,
    );

    expect(screen.getByText("100")).toBeInTheDocument();
  });

  test("test_critique_text_displayed", () => {
    const critique = "No logical issues detected.";

    render(
      <TrustScoreCard
        trustScore={80}
        hallucinationRisk="LOW"
        verdict="Supported."
        critique={critique}
      />,
    );

    expect(screen.getByText("Critique")).toBeInTheDocument();
    expect(screen.getByText(critique)).toBeInTheDocument();
  });
});
