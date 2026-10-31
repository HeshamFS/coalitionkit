// SPDX-License-Identifier: Apache-2.0
// The journey's moments, mounted in the room from the viewer's own feed state
// (docs/ux/journey.md: Theatre J-07, Overlap J-06, Ripple J-10, Chain J-12, Dissolve J-13).
import { ChainView } from "../chain/ChainView";
import { chainInputFrom } from "../chain/input";
import type { ViewerState } from "../feed/delta";
import { eventsOf } from "../feed/derive";
import { overlapFrom, rippleFrom, theatreFrom } from "../moments/adapters";
import { Dissolve } from "../moments/Dissolve";
import { Overlap } from "../moments/Overlap";
import { Ripple } from "../moments/Ripple";
import { Theatre } from "../moments/Theatre";

const has = (state: ViewerState | null, type: string) =>
  eventsOf(state).some((e) => e.type === type);

export function AgentsMoment({ state }: { state: ViewerState | null }) {
  return (
    <section className="room-moment" aria-label="Agents at work">
      <Theatre {...theatreFrom(state)} />
    </section>
  );
}

/**
 * A hosted vault's match result, which reaches only its own member as an agent line
 * `{"vault_result": {match_id, overlap?, count}}`. It is never in the log.
 */
export function vaultResult(lines: { text: string }[]) {
  for (const line of [...lines].reverse()) {
    try {
      const body = (JSON.parse(line.text) as { vault_result?: unknown }).vault_result;
      if (body && typeof body === "object") {
        const r = body as { overlap?: unknown; count?: unknown };
        const overlap = Array.isArray(r.overlap)
          ? r.overlap.filter((x) => typeof x === "string")
          : [];
        const count = typeof r.count === "number" ? r.count : overlap.length;
        return { shared: overlap.length ? overlap.join(", ") : `${count} in common` };
      }
    } catch {
      // Not a vault result line.
    }
  }
  return undefined;
}

/** Shown in My part once a private match involving the viewer has started. */
export function OverlapMoment({
  state,
  lines = [],
}: {
  state: ViewerState | null;
  lines?: { text: string }[];
}) {
  if (!has(state, "coalition.match")) return null;
  return (
    <section className="room-moment" aria-label="Private matching">
      <Overlap {...overlapFrom(state, { result: vaultResult(lines) })} />
    </section>
  );
}

/** Shown in Plans once there are tasks to draw. */
export function RippleMoment({ state }: { state: ViewerState | null }) {
  const props = rippleFrom(state);
  if (props.nodes.length === 0) return null;
  return (
    <section className="room-moment" aria-label="The plan as a living graph">
      <Ripple {...props} />
    </section>
  );
}

export function ChainMoment({ state }: { state: ViewerState | null }) {
  return (
    <section className="room-moment" aria-label="What happened">
      <ChainView input={chainInputFrom(state)} />
    </section>
  );
}

/** The final screen once the host has dissolved the coalition. */
export function dissolvedEvent(state: ViewerState | null) {
  const e = eventsOf(state).findLast((x) => x.type === "coalition.dissolve");
  if (!e) return null;
  const reason = String(e.payload.reason ?? "completed");
  const skills = Array.isArray(e.payload.skills_written)
    ? e.payload.skills_written.filter((s): s is string => typeof s === "string")
    : [];
  return { reason, skills_written: skills };
}

export function DissolveMoment({ state }: { state: ViewerState | null }) {
  const event = dissolvedEvent(state);
  if (!event) return null;
  return (
    <section className="room-moment" aria-label="The coalition has ended">
      <Dissolve event={event as Parameters<typeof Dissolve>[0]["event"]} />
    </section>
  );
}
