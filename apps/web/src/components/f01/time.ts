// SPDX-License-Identifier: Apache-2.0
/** Short viewer-local times; callers retain the original in dateTime and title. */
export function shortTime(value: string, timeZone?: string): string {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    ...(timeZone ? { timeZone } : {}),
  }).format(date);
}
