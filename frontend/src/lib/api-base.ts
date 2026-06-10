const LOCAL_API_BASE_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    if (
      process.env.NODE_ENV === "production" ||
      hostname === "aitrustanalyszer.vercel.app" ||
      hostname.endsWith(".vercel.app")
    ) {
      return "";
    }
  }

  const configuredUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configuredUrl) {
    return configuredUrl.replace(/\/+$/, "");
  }

  if (process.env.NODE_ENV === "production") {
    return "";
  }

  return LOCAL_API_BASE_URL;
}
