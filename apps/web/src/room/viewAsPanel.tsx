// SPDX-License-Identifier: Apache-2.0
// "View as": the menu, and the panel it rebuilds into. Composed from the viewer's own state only.
import { useEffect, useState } from "react";
import type { ViewerState } from "../feed/delta";
import { deriveParticipants } from "../feed/derive";
import { composeViewAs } from "./composeViewAs";
import { Germ } from "./germ";
import { Empty, PillTag, SeatAvatar } from "./parts";

export function ViewAsMenu({
  state,
  active,
  onPick,
  onLens,
}: {
  state: ViewerState | null;
  active: string | null;
  onPick: (id: string | null) => void;
  onLens: () => void;
}) {
  const [open, setOpen] = useState(false);
  const people = deriveParticipants(state);
  useEffect(() => {
    if (!open) return;
    const close = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [open]);
  const pick = (id: string | null) => {
    setOpen(false);
    onPick(id);
  };
  return (
    <div className="room-view-as">
      <button
        type="button"
        className="room-view-as-btn"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        View as…
      </button>
      {open && (
        <fieldset className="room-view-menu">
          <legend className="sr-only">View as</legend>
          <button type="button" aria-pressed={active === null} onClick={() => pick(null)}>
            Yourself
          </button>
          {people
            .filter((p) => p.id !== state?.viewer)
            .map((p) => (
              <button
                type="button"
                key={p.id}
                aria-pressed={active === p.id}
                onClick={() => pick(p.id)}
              >
                <SeatAvatar seat={p.seat} label={p.label} />
                {p.label}
              </button>
            ))}
          <button type="button" onClick={onLens}>
            Lens · your part
          </button>
        </fieldset>
      )}
    </div>
  );
}

/** The target's public summary as this viewer may see it. Never fetches anything. */
export function ViewAsPanel({
  state,
  target,
  ready,
  onBack,
}: {
  state: ViewerState | null;
  target: string;
  ready: boolean;
  onBack: () => void;
}) {
  const view = composeViewAs(state, target);
  if (!view) {
    return (
      <Germ index={0} ready={ready} label="PublicSummary">
        <Empty title="That member is not in your view" body="Go back to see your own view." />
        <button type="button" className="btn btn-sm" onClick={onBack}>
          Back to my view
        </button>
      </Germ>
    );
  }
  return (
    <section className="room-viewas" aria-label={`View as ${view.label}`}>
      <div className="room-viewas-bar">
        <p className="room-viewas-caption">{view.caption}</p>
        <button type="button" className="btn btn-sm" onClick={onBack}>
          Back to my view
        </button>
      </div>
      <Germ index={0} ready={ready} label="PublicSummary">
        <article className="room-participant" data-status={view.pill?.tone ?? "none"}>
          <div className="room-participant-head">
            <SeatAvatar seat={view.seat} label={view.label} />
            <span className="room-participant-name">{view.label}</span>
            {view.agent && <span className="room-participant-line">{view.agent}</span>}
          </div>
          <p className="room-item-detail">Seat {view.seat}</p>
          <PillTag pill={view.pill} />
        </article>
      </Germ>
      <Germ index={1} ready={ready} label="SharedWithYou">
        <article className="room-panel" aria-label="Shared with you">
          <h2>Shared with you</h2>
          {view.shared ? (
            <>
              <p className="room-current-item">{view.shared.item}</p>
              {view.shared.detail && <p className="room-item-detail">{view.shared.detail}</p>}
            </>
          ) : (
            <p className="room-item-detail">Private to them. Nothing is shared with you.</p>
          )}
        </article>
      </Germ>
      <Germ index={2} ready={ready} label="WhatTheyKnow">
        <article className="room-panel" aria-label="What they know">
          <h2>What they know</h2>
          {view.notes.length ? (
            <ul className="room-notes">
              {view.notes.map((n) => (
                <li key={`${n.knows}:${n.notKnows}`}>
                  Knows <b>{n.knows}</b>
                  {n.notKnows && (
                    <>
                      , not <b>{n.notKnows}</b>
                    </>
                  )}
                  {n.because && <span className="room-because"> · {n.because}</span>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="room-item-detail">Nothing about what they know is visible to you.</p>
          )}
        </article>
      </Germ>
    </section>
  );
}
