// SPDX-License-Identifier: Apache-2.0
// One component the host chose, drawn through the same catalog path as the room. It arrives as a
// labelled skeleton, fills and settles. Seats, the deadline and the needs can be changed in place.
import { useState } from "react";
import { One } from "../gallery/Drawn";
import type { Card, Draft } from "../genesis/api";
import { Assemble } from "../ui/Assemble";
import { PlaceMap } from "./PlaceMap";
import { seatTotal } from "./WhoCanFind";

/** The chosen component's props, with the writer's changes to the draft carried in. */
export function withEdits(card: Card, draft: Draft): Card {
  if (card.component === "SeatRing") {
    const shown = Array.isArray(card.props.seats) ? card.props.seats.length : 0;
    return { ...card, props: { ...card.props, openSeats: { value: Math.max(0, seatTotal(draft) - shown), event_ref: "draft:roles" } } };
  }
  if (card.component === "Deadline" && draft.deadline) {
    return { ...card, props: { ...card.props, deadline: draft.deadline } };
  }
  if (card.component === "Checklist") {
    return {
      ...card,
      props: { ...card.props, items: draft.needs.map((text) => ({ text, done: false })) },
    };
  }
  return card;
}

function SeatsEditor({ draft, onEdit }: { draft: Draft; onEdit: (patch: Partial<Draft>) => void }) {
  const set = (id: string, count: number) =>
    onEdit({ roles: draft.roles.map((r) => (r.id === id ? { ...r, count } : r)) });
  return (
    <ul className="fm-roles">
      {draft.roles.map((r) => {
        const n = r.count ?? 1;
        return (
          <li key={r.id}>
            <span>{r.label}</span>
            <span className="fm-step">
              <button
                type="button"
                aria-label={`One fewer ${r.label}`}
                disabled={n <= 1}
                onClick={() => set(r.id, n - 1)}
              >
                −
              </button>
              <output>{n}</output>
              <button
                type="button"
                aria-label={`One more ${r.label}`}
                disabled={n >= 64}
                onClick={() => set(r.id, n + 1)}
              >
                +
              </button>
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function localInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function NeedsEditor({ draft, onEdit }: { draft: Draft; onEdit: (patch: Partial<Draft>) => void }) {
  const [adding, setAdding] = useState("");
  return (
    <form
      className="fm-add"
      onSubmit={(e) => {
        e.preventDefault();
        if (adding.trim()) onEdit({ needs: [...draft.needs, adding.trim()] });
        setAdding("");
      }}
    >
      <label className="sr-only" htmlFor="fm-need">
        Add something that needs doing
      </label>
      <input
        id="fm-need"
        value={adding}
        maxLength={120}
        placeholder="Add something that needs doing"
        onChange={(e) => setAdding(e.target.value)}
      />
      <button type="submit" disabled={!adding.trim()}>
        Add
      </button>
    </form>
  );
}

export function FormingCard({
  card,
  draft,
  delay,
  hot,
  onHot,
  onEdit,
}: {
  card: Card;
  draft: Draft;
  delay: number;
  hot: boolean;
  onHot: (word: string | null) => void;
  onEdit: (patch: Partial<Draft>) => void;
}) {
  const { title } = card;
  return (
    <section
      className="fm-card"
      data-size={card.size}
      data-hot={hot}
      data-component-card={card.component}
      aria-label={title}
      onMouseEnter={() => card.word && onHot(card.word)}
      onMouseLeave={() => card.word && onHot(null)}
    >
      <Assemble ready label={card.component} delay={delay}>
        <div className="fm-card-head">
          <b>{title}</b>
          {!(card.component === "MapView" && draft.place) && <span>{card.component}</span>}
        </div>
        <div className="fm-card-body">
          {card.component === "MapView" && draft.place ? (
            <PlaceMap place={draft.place} seats={seatTotal(draft)} />
          ) : (
            <One component={card.component} props={card.props} />
          )}
        </div>
        {card.component === "SeatRing" && <SeatsEditor draft={draft} onEdit={onEdit} />}
        {card.component === "Deadline" && (
          <label className="fm-when">
            <span className="sr-only">Change when this closes</span>
            <input
              type="datetime-local"
              value={localInput(draft.deadline)}
              onChange={(e) =>
                onEdit({ deadline: e.target.value ? new Date(e.target.value).toISOString() : null })
              }
            />
          </label>
        )}
        {card.component === "Checklist" && <NeedsEditor draft={draft} onEdit={onEdit} />}
        {card.word && <span className="fm-from">from “{card.word}”</span>}
      </Assemble>
    </section>
  );
}
