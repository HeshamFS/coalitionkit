// SPDX-License-Identifier: Apache-2.0
// Words and tones for the status pill, from the state words that `deriveParticipants` produces.

export type PillTone = "agreed" | "needs" | "changed" | "private" | "blocked";
export type Pill = { tone: PillTone; word: string };

/** The design system's states: Agreed, Needs you, Changed, Private, Blocked. */
export function pillFor(status: string, opts: { own: boolean; hasItem: boolean }): Pill | null {
  const s = status.trim();
  if (s === "Agreed") return { tone: "agreed", word: "Agreed" };
  if (s.startsWith("Changed")) return { tone: "changed", word: "Changed" };
  if (s.startsWith("Blocked")) return { tone: "blocked", word: "Blocked" };
  if (s.startsWith("Needs")) {
    return { tone: "needs", word: opts.own ? "Needs you" : "Needs their yes" };
  }
  if (!s && !opts.hasItem) return { tone: "private", word: "Private" };
  return null;
}

export const PILL_CLASS: Record<PillTone, string> = {
  agreed: "t-agreed",
  needs: "t-needs",
  changed: "t-changed",
  private: "t-private",
  blocked: "t-blocked",
};

/** Two letters for a seat avatar: "Member 2" gives "M2", "Ada Byron" gives "AB". */
export function initialsOf(label: string): string {
  return label
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

/** "Agent on Vendor", or whichever half is known. */
export function agentLine(agent: string, vendor: string): string {
  if (agent && vendor) return `${agent} on ${vendor}`;
  return agent || vendor;
}
