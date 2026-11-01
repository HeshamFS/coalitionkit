// SPDX-License-Identifier: Apache-2.0
// Plain words for plan objectives. Every objective is a number where lower is better (the
// planner minimises them all). Keys the kit knows get a fixed phrase; any other key is only
// turned from snake_case into words, never given a meaning of its own.

type Scored = { name: string; value: number };

const KNOWN: Record<string, { short: string; best: string; unit?: string }> = {
  total_cost: { short: "cost", best: "lowest total cost" },
  max_share_ratio: { short: "largest share", best: "fairest split", unit: "×" },
};

const words = (key: string) => key.replace(/[_-]+/g, " ").trim();

/** "third" reads as "third goal"; names that already say what they are stay as they are. */
export function objectiveWords(key: string): string {
  const w = words(key);
  return w.split(" ").length === 1 && !KNOWN[key] ? `${w} goal` : w;
}

const shortOf = (key: string) => KNOWN[key]?.short ?? objectiveWords(key);

/** One measured value for the quiet line, e.g. "cost 360" or "largest share 2×". */
export function measuredPhrase(o: Scored): string {
  return `${shortOf(o.name)} ${o.value}${KNOWN[o.name]?.unit ?? ""}`;
}

/** What each plan is best at (strictly lowest of all plans) and what it gives up. */
export function planStrengths(all: Scored[][]): string[] {
  return all.map((mine, index) => {
    const best: string[] = [];
    const worse: string[] = [];
    for (const o of mine) {
      const others = all
        .filter((_, i) => i !== index)
        .map((p) => p.find((x) => x.name === o.name)?.value)
        .filter((v): v is number => typeof v === "number");
      if (!others.length) continue;
      if (others.every((v) => o.value < v)) {
        best.push(KNOWN[o.name]?.best ?? `lowest ${objectiveWords(o.name)}`);
      } else if (others.every((v) => o.value > v) && KNOWN[o.name]) {
        worse.push(`higher ${shortOf(o.name)}`);
      }
    }
    return [...best, ...worse].join(" · ");
  });
}
