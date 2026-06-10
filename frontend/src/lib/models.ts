export const PROCESSING_MODEL = {
  value: "gemini-3.1-flash-lite",
  label: "Gemini 3.1 Flash Lite",
};

export const RESPONSE_MODELS = [
  { value: "gpt-4o", label: "GPT-4o" },
  { value: "gpt-4.1", label: "GPT-4.1" },
  { value: "gpt-4.1-mini", label: "GPT-4.1 Mini" },
  { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
  { value: "claude-sonnet", label: "Claude Sonnet" },
  { value: "claude-opus", label: "Claude Opus" },
  { value: "claude-haiku", label: "Claude Haiku" },
  { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro" },
  { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
  { value: "gemini-3.1-flash-lite", label: "Gemini 3.1 Flash Lite" },
  { value: "gemini-3.1-pro", label: "Gemini 3.1 Pro" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "grok", label: "Grok" },
  { value: "llama", label: "Llama" },
];

export function modelLabel(value: string | null | undefined): string {
  if (!value) return "Unknown model";
  return RESPONSE_MODELS.find((model) => model.value === value)?.label ?? value;
}
