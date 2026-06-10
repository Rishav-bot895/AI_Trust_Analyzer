"use client";

import { useState } from "react";
import type { AnalysisRequest } from "../types/api";
import { getOrCreateGuestSessionId } from "../lib/guest-session";

interface AnalysisInputFormProps {
  onSubmit: (request: AnalysisRequest) => Promise<void>;
  isLoading: boolean;
}

const MODELS = [
  { value: "gpt-4o",            label: "GPT-4o" },
  { value: "gpt-4o-mini",       label: "GPT-4o Mini" },
  { value: "gpt-4-turbo",       label: "GPT-4 Turbo" },
  { value: "claude-3-5-sonnet", label: "Claude 3.5 Sonnet" },
  { value: "claude-3-haiku",    label: "Claude 3 Haiku" },
  { value: "gemini-1.5-pro",    label: "Gemini 1.5 Pro" },
];

export function AnalysisInputForm({ onSubmit, isLoading }: AnalysisInputFormProps) {
  const [prompt, setPrompt]       = useState("");
  const [response, setResponse]   = useState("");
  const [modelName, setModelName] = useState(MODELS[0].value);
  const [touched, setTouched]     = useState({ prompt: false, response: false });

  const promptError   = touched.prompt   && prompt.trim().length   < 10;
  const responseError = touched.response && response.trim().length < 10;
  const canSubmit     = prompt.trim().length >= 10 && response.trim().length >= 10 && !isLoading;

  async function handleSubmit() {
    setTouched({ prompt: true, response: true });
    if (!canSubmit) return;

    const guestSessionId = getOrCreateGuestSessionId();
    await onSubmit({
      prompt:         prompt.trim(),
      response:       response.trim(),
      modelName,
      userMode:       "GUEST",
      guestSessionId: guestSessionId ?? undefined,
    });
  }

  return (
    <div className="card w-full p-6 space-y-6">

      {/* Header */}
      <div className="space-y-1">
        <p className="label">New Analysis</p>
        <h2
          className="text-2xl text-text-primary"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          Verify an AI Response
        </h2>
        <p className="text-sm text-text-secondary">
          Paste the original prompt and the AI-generated response you want to fact-check.
        </p>
      </div>

      {/* Model selector */}
      <div className="space-y-2">
        <label className="label">Model that generated the response</label>
        <div className="flex flex-wrap gap-2">
          {MODELS.map((m) => (
            <button
              key={m.value}
              type="button"
              onClick={() => setModelName(m.value)}
              className={`px-3 py-1 text-xs rounded transition-colors ${
                modelName === m.value
                  ? "bg-accent text-surface font-medium"
                  : "border border-border text-text-secondary hover:border-accent hover:text-accent"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* Prompt */}
      <div className="space-y-2">
        <label className="label">Original Prompt</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onBlur={() => setTouched((t) => ({ ...t, prompt: true }))}
          placeholder="What question or instruction was given to the AI?"
          rows={4}
          className={`w-full bg-surface-high border rounded-md px-4 py-3 text-sm text-text-primary
            placeholder:text-text-muted resize-none outline-none transition-colors
            focus:border-accent
            ${promptError ? "border-refuted" : "border-border"}`}
        />
        {promptError && (
          <p className="text-xs text-refuted">Please enter at least 10 characters.</p>
        )}
      </div>

      {/* AI Response */}
      <div className="space-y-2">
        <label className="label">AI-Generated Response</label>
        <textarea
          value={response}
          onChange={(e) => setResponse(e.target.value)}
          onBlur={() => setTouched((t) => ({ ...t, response: true }))}
          placeholder="Paste the AI response you want to analyze for hallucinations…"
          rows={7}
          className={`w-full bg-surface-high border rounded-md px-4 py-3 text-sm text-text-primary
            placeholder:text-text-muted resize-none outline-none transition-colors
            focus:border-accent
            ${responseError ? "border-refuted" : "border-border"}`}
        />
        {responseError && (
          <p className="text-xs text-refuted">Please enter at least 10 characters.</p>
        )}
      </div>

      {/* Submit */}
      <button
        type="button"
        onClick={() => void handleSubmit()}
        disabled={!canSubmit}
        className={`w-full py-3 rounded-md text-sm font-medium tracking-widest uppercase transition-all
          ${canSubmit
            ? "bg-accent text-surface hover:brightness-110 active:scale-[0.98]"
            : "bg-surface-high text-text-muted cursor-not-allowed border border-border"
          }`}
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="inline-block w-3 h-3 border border-surface border-t-transparent rounded-full animate-spin" />
            Analyzing…
          </span>
        ) : (
          "Analyze Response"
        )}
      </button>
    </div>
  );
}