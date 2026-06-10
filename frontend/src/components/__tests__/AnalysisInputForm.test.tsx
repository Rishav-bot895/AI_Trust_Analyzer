import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { AnalysisInputForm } from "../AnalysisInputForm";

const guestSessionIdMock = vi.fn(() => "guest-session-123");

vi.mock("../../lib/guest-session", () => ({
  getOrCreateGuestSessionId: () => guestSessionIdMock(),
}));

describe("AnalysisInputForm", () => {
  beforeEach(() => {
    guestSessionIdMock.mockClear();
  });

  test("test_submit_button_disabled_when_empty", () => {
    render(
      <AnalysisInputForm
        onSubmit={vi.fn(async () => undefined)}
        isLoading={false}
        userMode="GUEST"
      />,
    );

    expect(
      screen.getByRole("button", { name: "Analyze Response" }),
    ).toBeDisabled();
  });

  test("test_character_count_updates", async () => {
    const user = userEvent.setup();
    const responseText = "This response is definitely longer than fifty characters to pass validation.";

    render(
      <AnalysisInputForm
        onSubmit={vi.fn(async () => undefined)}
        isLoading={false}
        userMode="GUEST"
      />,
    );

    await user.type(screen.getByLabelText("Original Prompt"), "Hello prompt");
    await user.type(screen.getByLabelText("AI Response to Analyze"), responseText);

    expect(screen.getByText("12/2000")).toBeInTheDocument();
    expect(screen.getByText(`${responseText.length}/10000`)).toBeInTheDocument();
  });

  test("test_validation_error_shown_on_short_response", async () => {
    const user = userEvent.setup();
    const submit = vi.fn(async () => undefined);

    render(
      <AnalysisInputForm onSubmit={submit} isLoading={false} userMode="GUEST" />,
    );

    await user.type(screen.getByLabelText("Original Prompt"), "A valid prompt");
    await user.type(screen.getByLabelText("AI Response to Analyze"), "Too short");
    await user.click(screen.getByRole("button", { name: "Analyze Response" }));

    expect(
      await screen.findByText("Please enter at least 50 characters."),
    ).toBeInTheDocument();
    expect(submit).not.toHaveBeenCalled();
  });

  test("test_form_resets_after_submit", async () => {
    const user = userEvent.setup();
    const submit = vi.fn(async () => undefined);

    render(
      <AnalysisInputForm onSubmit={submit} isLoading={false} userMode="GUEST" />,
    );

    const prompt = screen.getByLabelText("Original Prompt") as HTMLTextAreaElement;
    const response = screen.getByLabelText("AI Response to Analyze") as HTMLTextAreaElement;

    await user.type(prompt, "Prompt content");
    await user.type(response, "This response is definitely longer than fifty characters to pass validation.");
    await user.click(screen.getByRole("button", { name: "Analyze Response" }));

    await waitFor(() => {
      expect(submit).toHaveBeenCalledTimes(1);
    });

    expect(prompt.value).toBe("");
    expect(response.value).toBe("");
  });

  test("test_valid_guest_submit_includes_trimmed_payload_and_guest_session", async () => {
    const user = userEvent.setup();
    const submit = vi.fn(async () => undefined);
    const responseText = "This response is definitely longer than fifty characters to pass validation.";

    render(<AnalysisInputForm onSubmit={submit} isLoading={false} userMode="GUEST" />);

    await user.type(screen.getByLabelText("Original Prompt"), "  Prompt content  ");
    await user.type(screen.getByLabelText("AI Response to Analyze"), `  ${responseText}  `);
    await user.click(screen.getByRole("button", { name: "Analyze Response" }));

    await waitFor(() => {
      expect(submit).toHaveBeenCalledWith({
        prompt: "Prompt content",
        response: responseText,
        modelName: "gpt-4o",
        userMode: "GUEST",
        guestSessionId: "guest-session-123",
      });
    });
    expect(guestSessionIdMock).toHaveBeenCalledTimes(1);
  });

  test("test_authenticated_submit_omits_guest_session", async () => {
    const user = userEvent.setup();
    const submit = vi.fn(async () => undefined);

    render(
      <AnalysisInputForm
        onSubmit={submit}
        isLoading={false}
        userMode="AUTHENTICATED"
      />,
    );

    await user.type(screen.getByLabelText("Original Prompt"), "Prompt content");
    await user.type(
      screen.getByLabelText("AI Response to Analyze"),
      "This response is definitely longer than fifty characters to pass validation.",
    );
    await user.click(screen.getByRole("button", { name: "Analyze Response" }));

    await waitFor(() => {
      expect(submit).toHaveBeenCalledTimes(1);
    });
    expect(submit.mock.calls[0][0].guestSessionId).toBeUndefined();
    expect(submit.mock.calls[0][0]).toMatchObject({ userMode: "AUTHENTICATED" });
    expect(guestSessionIdMock).not.toHaveBeenCalled();
  });

  test("test_loading_state_disables_button_and_shows_spinner_text", () => {
    render(
      <AnalysisInputForm
        onSubmit={vi.fn(async () => undefined)}
        isLoading
        userMode="GUEST"
      />,
    );

    const button = screen.getByRole("button", { name: /Analyzing/i });
    expect(button).toBeDisabled();
    expect(screen.getByText(/Analyzing/)).toBeInTheDocument();
  });

  test("test_model_dropdown_lists_supported_response_models", () => {
    render(
      <AnalysisInputForm
        onSubmit={vi.fn(async () => undefined)}
        isLoading={false}
        userMode="GUEST"
      />,
    );

    expect(screen.getByRole("option", { name: "GPT-4o" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Claude Sonnet" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Gemini 2.5 Pro" })).toBeInTheDocument();
    expect(screen.getByText("Internal analysis runs on Gemini 3.1 Flash Lite.")).toBeInTheDocument();
  });
});
