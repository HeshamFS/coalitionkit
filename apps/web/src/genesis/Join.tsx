// SPDX-License-Identifier: Apache-2.0
// Arriving at a room from a link, a QR or a spoken code: no account and no install. A room code shows
// the goal and its open seats first; an invitation for one person is exchanged and dies.
import { useEffect, useState } from "react";
import { pinAtJoin } from "../chain/pin";
import { saveToken } from "../feed/config";
import { RoomMark } from "../landing/marks";
import { PublicNav } from "../landing/PublicNav";
import { doorCodeIn } from "../landing/rooms";
import { acceptInvitation, type DoorCard, HostError, joinByCode, readDoorCard } from "./api";
import { takeInvitation } from "./fragment";
import "./genesis.css";
import "../landing/landing.css";
import "../forming/forming.css";

function refused(e: unknown, code: boolean): string {
  if (!(e instanceof HostError)) return "The host could not be reached.";
  if (e.status === 409) return "This room is full.";
  if (e.status === 429) return "Too many tries. Wait a minute.";
  if (code) return "This code has stopped working. Ask for a new one.";
  return e.status === 400
    ? "This invitation has been used or withdrawn. Ask for a new link."
    : "The host could not be reached.";
}

export function Join({ onJoined }: { onJoined: () => void }) {
  const [invitation] = useState(() => takeInvitation());
  const code = doorCodeIn(invitation);
  const [card, setCard] = useState<DoorCard | null>(null);
  const [seat, setSeat] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(
    invitation ? "" : "This link has no invitation in it. Ask for a new link.",
  );
  useEffect(() => {
    if (!code) return;
    readDoorCard(code)
      .then((c) => {
        setCard(c);
        setSeat(c.roles.find((r) => r.open > 0)?.id ?? "");
      })
      .catch((e) => setError(refused(e, true)));
  }, [code]);
  const join = async () => {
    setBusy(true);
    try {
      const joined = code
        ? await joinByCode(code, "", seat)
        : await acceptInvitation(invitation, "");
      saveToken(joined.token);
      pinAtJoin(joined.coalition_id, joined.host_key);
      onJoined();
    } catch (e) {
      setError(refused(e, Boolean(code)));
    } finally {
      setBusy(false);
    }
  };
  const blocked = !invitation || busy || (Boolean(code) && !card);
  return (
    <div className="ld fm">
      <PublicNav onJoin={(secret) => globalThis.location.assign(`/join#${secret}`)} />
      <main>
        <section className="ld-hero fm-hero">
          <p className="ld-eyebrow">You're invited</p>
          <h1 className="ld-title fm-sentence">
            {card ? (
              card.goal
            ) : (
              <>
                A goal with a seat <em>for you.</em>
              </>
            )}
          </h1>
          <p className="ld-sub">
            A room is a group of people and their agents working toward one goal. You see only your
            part.
          </p>
        </section>
        <div className="ld-mapwrap fm-wrap">
          <form
            className="fm-join"
            onSubmit={(e) => {
              e.preventDefault();
              if (!blocked) void join();
            }}
          >
            {card && (
              <div className="fm-join-room">
                <RoomMark seats={card.seats} filled={card.filled} size={64} />
                <b>
                  {card.filled} of {card.seats} seats taken
                </b>
              </div>
            )}
            <ul className="fm-join-list">
              <li>
                <b>Others see</b> your seat, and what you agree to after you say yes.
              </li>
              <li>
                <b>Nobody sees</b> your reasons, limits or free time.
              </li>
              <li>
                <b>Nothing commits you</b> until you press and hold to sign.
              </li>
            </ul>
            {card && card.roles.length > 1 && (
              <fieldset className="fm-fieldset fm-seats">
                <legend>Which seat fits you?</legend>
                {card.roles.map((r) => (
                  <label key={r.id} data-on={seat === r.id} data-off={r.open < 1}>
                    <input
                      type="radio"
                      name="fm-seat"
                      className="sr-only"
                      checked={seat === r.id}
                      disabled={r.open < 1}
                      onChange={() => setSeat(r.id)}
                    />
                    <b>{r.label}</b>
                    <small>{r.open > 0 ? `${r.open} open` : "taken"}</small>
                  </label>
                ))}
              </fieldset>
            )}
            {error && (
              <p className="fm-error" role="alert">
                {error}
              </p>
            )}
            <button type="submit" className="fm-go" disabled={blocked}>
              {busy ? "Joining…" : "Take a seat"}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
