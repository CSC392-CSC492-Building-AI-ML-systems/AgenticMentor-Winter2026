/**
 * Turn FastAPI error response (string or validation list) into a single string
 * so we never pass an object/array to setState and then render as React child.
 */
export function formatApiError(detail: unknown): string {
  if (detail == null) return "Something went wrong.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .filter((d): d is { msg?: string; loc?: unknown } => typeof d === "object" && d !== null)
      .map((d) => d.msg ?? "Validation error")
      .filter(Boolean);
    return messages.length ? messages.join(". ") : "Validation failed.";
  }
  if (typeof detail === "object" && "message" in detail && typeof (detail as { message: unknown }).message === "string") {
    return (detail as { message: string }).message;
  }
  return "Something went wrong.";
}
