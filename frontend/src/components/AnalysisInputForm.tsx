"use client";

import { useState } from "react";
import type { AnalysisRequest, UserMode } from "../types/api";
import { getOrCreateGuestSessionId } from "../lib/guest-session";
import { PROCESSING_MODEL, RESPONSE_MODELS } from "../lib/models";

interface AnalysisInputFormProps {
  onSubmit: (request: AnalysisRequest) => Promise<void>;
  isLoading: boolean;
  userMode: UserMode;
}

const PROMPT_MAX_CHARS = 2000;
const RESPONSE_MAX_CHARS = 10000;
const RESPONSE_MIN_CHARS = 50;
const WARNING_THRESHOLD = 0.9;

export function AnalysisInputForm({ onSubmit, isLoading, userMode }: AnalysisInputFormProps) {
  const [prompt, setPrompt]       = useState("");
  const [response, setResponse]   = useState("");
  const [modelName, setModelName] = useState(RESPONSE_MODELS[0].value);
  const [touched, setTouched]     = useState({ prompt: false, response: false });

  const promptLength = prompt.length;
  const responseLength = response.length;
  const promptTrimmed = prompt.trim();
  const responseTrimmed = response.trim();
  const promptWarning = promptLength >= Math.floor(PROMPT_MAX_CHARS * WARNING_THRESHOLD);
  const responseWarning = responseLength >= Math.floor(RESPONSE_MAX_CHARS * WARNING_THRESHOLD);

  const promptError = touched.prompt && promptTrimmed.length === 0;
  const responseError = touched.response && responseTrimmed.length < RESPONSE_MIN_CHARS;
  const canSubmit = promptTrimmed.length > 0 && responseTrimmed.length >= RESPONSE_MIN_CHARS && !isLoading;

  async function handleSubmit() {
    setTouched({ prompt: true, response: true });
    if (!canSubmit) return;

    const guestSessionId = userMode === "GUEST" ? getOrCreateGuestSessionId() : null;
    await onSubmit({
      prompt: promptTrimmed,
      response: responseTrimmed,
      modelName,
      userMode,
      guestSessionId: guestSessionId ?? undefined,
    });

    setPrompt("");
    setResponse("");
    setTouched({ prompt: false, response: false });
  }

  return (
    <div className="card w-full p-6 space-y-6">

      {/* Header */}
      <div className="space-y-1">
        <p className="label">New Analysis</p>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-2xl text-text-primary" style={{ fontFamily: "var(--font-serif)" }}>
            Verify an AI Response
          </h2>
          <span className="rounded-full border border-border bg-surface-high px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-text-secondary">
            {userMode === "AUTHENTICATED" ? "Authenticated mode" : "Guest mode"}
          </span>
        </div>
        <p className="text-sm text-text-secondary">
          Paste the original prompt and the AI-generated response you want to fact-check.
        </p>
      </div>

      {/* Model selector */}
      <div className="space-y-2">
        <label htmlFor="analysis-model" className="label">Model that generated the response</label>
        <select
          id="analysis-model"
          value={modelName}
          onChange={(e) => setModelName(e.target.value)}
          className="w-full rounded-md border border-border bg-surface-high px-3 py-2 text-sm text-text-primary outline-none transition-colors focus:border-accent"
        >
          {RESPONSE_MODELS.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
        <p className="text-xs text-text-muted">
          Internal analysis runs on {PROCESSING_MODEL.label}.
        </p>
      </div>

      {/* Prompt */}
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <label htmlFor="analysis-prompt" className="label">Original Prompt</label>
          <span className={`text-xs ${promptWarning ? "text-uncertain" : "text-text-muted"}`}>
            {promptLength}/{PROMPT_MAX_CHARS}
          </span>
        </div>
        <textarea
          id="analysis-prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onBlur={() => setTouched((t) => ({ ...t, prompt: true }))}
          placeholder="What question or instruction was given to the AI?"
          rows={4}
          maxLength={PROMPT_MAX_CHARS}
          className={`w-full bg-surface-high border rounded-md px-4 py-3 text-sm text-text-primary
            placeholder:text-text-muted resize-none outline-none transition-colors
            focus:border-accent
            ${promptError ? "border-refuted" : "border-border"}`}
        />
        {promptError && (
          <p className="text-xs text-refuted">Original prompt is required.</p>
        )}
      </div>

      {/* AI Response */}
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <label htmlFor="analysis-response" className="label">AI Response to Analyze</label>
          <span className={`text-xs ${responseWarning ? "text-uncertain" : "text-text-muted"}`}>
            {responseLength}/{RESPONSE_MAX_CHARS}
          </span>
        </div>
        <textarea
          id="analysis-response"
          value={response}
          onChange={(e) => setResponse(e.target.value)}
          onBlur={() => setTouched((t) => ({ ...t, response: true }))}
          placeholder="Paste the AI response you want to analyze for hallucinations…"
          rows={7}
          maxLength={RESPONSE_MAX_CHARS}
          className={`w-full bg-surface-high border rounded-md px-4 py-3 text-sm text-text-primary
            placeholder:text-text-muted resize-none outline-none transition-colors
            focus:border-accent
            ${responseError ? "border-refuted" : "border-border"}`}
        />
        {responseError && (
          <p className="text-xs text-refuted">Please enter at least 50 characters.</p>
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
