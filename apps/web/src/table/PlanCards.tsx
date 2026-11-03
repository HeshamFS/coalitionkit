// SPDX-License-Identifier: Apache-2.0
// The plans side by side. The numbers are the host's measured ones from `derivePlans`; the name
// and the one line are the Gardener's (marked model or rules); the "for you only" line is private
// to this viewer. Choosing a card only opens the yes for it. It signs nothing.
import type { Plan } from "../components/f06/plans";
import type { Room } from "./room";

const nameOf = (p: Plan, room: Room) => {
  const named = room.plan_notes[p.id]?.name;
  if (named) return named;
  const after = p.label.split(" · ").slice(1).join(" · ");
  return after || `Plan ${p.short ?? ""}`.trim();
};

export function PlanCards({
  plans,
  room,
  selected,
  signed,
  onPick,
  placement,
}: {
  plans: Plan[];
  room: Room;
  selected: string | null;
  /** Plan ids the viewer already said yes to. */
  signed: ReadonlySet<string>;
  onPick: (id: string) => void;
  placement: "strip" | "side";
}) {
  if (plans.length === 0) {
    return (
      <p className="tb-quiet" role="status">
        No plan is on the table yet. The Gardener is still building them.
      </p>
    );
  }
  return (
    <fieldset className="tb-plans" data-placement={placement}>
      <legend className="tb-sr">Plans</legend>
      {plans.map((p) => {
        const note = room.plan_notes[p.id];
        const mine = room.mine.for_you[p.id];
        return (
          <button
            key={p.id}
            type="button"
            className="tb-plan"
            data-on={selected === p.id}
            aria-pressed={selected === p.id}
            onClick={() => onPick(p.id)}
          >
            <span className="tb-plan-k">
              PLAN {p.short}
              {signed.has(p.id) || p.highlight ? " · YOUR YES" : ""}
            </span>
            <span className="tb-plan-h">{nameOf(p, room)}</span>
            {note?.line && <span className="tb-plan-line">{note.line}</span>}
            {note && (
              <span className="tb-plan-src">
                named by the {note.source === "model" ? "model" : "rules"}
              </span>
            )}
            {mine && (
              <span className="tb-plan-fy">
                <b>FOR YOU ONLY</b>
                {mine}
              </span>
            )}
          </button>
        );
      })}
    </fieldset>
  );
}
