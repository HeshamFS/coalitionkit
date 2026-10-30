// SPDX-License-Identifier: Apache-2.0
import { z } from "zod";

/** Nested catalog data uses the same provenance rule as top-level number props. */
function boundNumbers(value: unknown): boolean {
  if (typeof value === "number") return false;
  if (Array.isArray(value)) return value.every(boundNumbers);
  if (!value || typeof value !== "object") return true;
  const record = value as Record<string, unknown>;
  if (typeof record.value === "number") {
    if (!Number.isFinite(record.value) || typeof record.event_ref !== "string" || !record.event_ref)
      return false;
    return Object.entries(record).every(([key, child]) => key === "value" || boundNumbers(child));
  }
  return Object.values(record).every(boundNumbers);
}
export const WireValue = z.unknown().refine(boundNumbers, "Numbers require {value, event_ref}");
