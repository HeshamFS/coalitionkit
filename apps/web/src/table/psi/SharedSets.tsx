// SPDX-License-Identifier: Apache-2.0
// What the vaults found in common, set by set: the sets a pack declares are compared by private
// set intersection, so the room shows only the shared values (or only how many there are) and
// each person sees how many of their own stayed private. Every word and number comes from the
// host's `room.sets` and the viewer's own `room.mine.sets`; nothing here is computed from a list.
import type { Room, SharedSet } from "../room";
import "./sets.css";

function Lock() {
  return (
    <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true" className="ps-lock">
      <rect x="3" y="7" width="10" height="7" rx="1.5" fill="currentColor" />
      <path d="M5 7V5a3 3 0 0 1 6 0v2" fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

const who = (n: number) => (n === 2 ? "you both" : n > 2 ? `all ${n}` : "everyone");

/** The line under a set: who compared and, for the viewer, what stayed private. */
export function setNote(set: SharedSet, mine: number | undefined): string {
  if (set.state !== "done") return "Comparing privately…";
  const published = set.values !== null || set.count !== null;
  if (!published) return "Too few gave theirs; nothing was shared.";
  const base = `Compared by ${set.compared}`;
  if (mine === undefined) return `${base}. You sat this one out.`;
  return `${base}. Your other ${mine} stayed private.`;
}

/** The finding itself: the shared values, or only the count. */
export function setFinding(set: SharedSet): string | null {
  if (set.state !== "done") return null;
  if (set.values !== null) {
    return set.values.length ? `Fits ${who(set.compared)}` : `Nothing fits ${who(set.compared)}`;
  }
  if (set.count !== null) return `${set.count} in common, which ones stays private`;
  return null;
}

export function SharedSets({ room }: { room: Room }) {
  const sets = room.sets ?? [];
  if (!sets.length) return null;
  const mine = room.mine.sets ?? {};
  return (
    <section className="ps-sets" aria-label="Found in common, privately">
      <header>
        <Lock /> Found in common, privately
      </header>
      {sets.map((s) => {
        const finding = setFinding(s);
        return (
          <article key={s.id} className="ps-set" data-state={s.state} data-mode={s.mode}>
            <b>{s.label}</b>
            {finding && <span className="ps-finding">{finding}</span>}
            {s.values && s.values.length > 0 && (
              <ul className="ps-values">
                {s.values.map((v) => (
                  <li key={v}>{v}</li>
                ))}
              </ul>
            )}
            {s.mode === "count" && s.count !== null && (
              <span className="ps-count" aria-hidden="true">
                {s.count}
              </span>
            )}
            <small>{setNote(s, mine[s.id])}</small>
          </article>
        );
      })}
    </section>
  );
}
