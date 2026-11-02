// SPDX-License-Identifier: Apache-2.0
// The one question before a room opens. It suggests from the sentence, the opener decides, and it
// shows exactly what goes public first. "People nearby" means a pin on this host's map for now.
import type { Draft, Visibility } from "../genesis/api";

export function seatTotal(draft: Draft): number {
  return draft.roles.reduce((n, r) => n + Math.max(1, r.count ?? 1), 0);
}

export function seatWords(draft: Draft): string {
  const n = seatTotal(draft);
  return `${n} ${n === 1 ? "seat" : "seats"}`;
}

export function WhoCanFind({
  draft,
  value,
  busy,
  onChange,
  onBack,
  onOpen,
}: {
  draft: Draft;
  value: Visibility;
  busy: boolean;
  onChange: (v: Visibility) => void;
  onBack: () => void;
  onOpen: () => void;
}) {
  const place = draft.place ?? null;
  const options: {
    id: Visibility;
    label: string;
    about: string;
    off?: boolean;
    why?: string;
  }[] = [
    {
      id: "code",
      label: "Only with the code",
      about: "QR, code or link. Not listed anywhere. Distance doesn't matter.",
      why: place ? undefined : "Suggested: your sentence names no place to pin.",
    },
    {
      id: "nearby",
      label: "People nearby",
      about: place
        ? "A pin on this host's map. People knock to come in, and you answer."
        : "Your sentence names no single place, so there is nothing to pin.",
      off: !place,
      why: place ? `Suggested: your sentence names ${place}.` : undefined,
    },
  ];
  return (
    <div className="fm-who">
      <fieldset className="fm-fieldset">
        <legend>Who can find this room?</legend>
        {options.map((o) => (
          <label key={o.id} className="fm-opt" data-on={value === o.id} data-off={Boolean(o.off)}>
            <input
              type="radio"
              name="fm-who"
              className="fm-radio"
              checked={value === o.id}
              disabled={o.off || busy}
              onChange={() => onChange(o.id)}
            />
            <span>
              <b>{o.label}</b>
              <small>{o.about}</small>
              {o.why && <small className="fm-why">{o.why}</small>}
            </span>
          </label>
        ))}
      </fieldset>
      <div className="fm-who-side">
        <div className="fm-public">
          {value === "nearby" ? (
            <>
              <b>What becomes public</b>
              <q>{draft.goal}</q>
              <span>
                {place ? `Pin at ${place}. ` : ""}
                {seatWords(draft)}. It leaves the map when it closes, fills or you stop it. Your
                name doesn't show.
              </span>
            </>
          ) : (
            <>
              <b>Nothing is listed</b>
              <span>
                This room isn't on the map. Only people you give the code, QR or link to can reach
                it.
              </span>
            </>
          )}
        </div>
        <div className="fm-who-actions">
          <button type="button" className="fm-ghost" disabled={busy} onClick={onBack}>
            Back
          </button>
          <button type="button" className="fm-go" disabled={busy} onClick={onOpen}>
            {busy ? "Opening…" : "Open the room"}
          </button>
        </div>
      </div>
    </div>
  );
}
