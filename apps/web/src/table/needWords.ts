// SPDX-License-Identifier: Apache-2.0
// Plain words for where a need stands. The host's own status words stay in "Show the work".
const WORDS: Record<string, string> = {
  open: "waiting for offers",
  negotiating: "agents comparing",
  offered: "offers in",
  proposed: "in a plan",
  decided: "agreed",
  committed: "being done",
  making: "being made",
  ready: "ready",
  "re-planning": "being re-planned",
  replanning: "being re-planned",
  done: "done",
};

/** What to show under a need: a plain status, with the offer count while offers are what matter. */
export function needStatus(status: string, offers: number, kind: string): string {
  const key = status
    .trim()
    .toLowerCase()
    .replace(/[_\s]+/g, "-");
  const word = WORDS[key] ?? "";
  const count =
    offers > 0 && (key === "" || key === "open" || key === "negotiating" || key === "offered");
  const tail = count ? ` · ${offers} ${offers === 1 ? "offer" : "offers"}` : "";
  return `${word || kind}${tail}`;
}
