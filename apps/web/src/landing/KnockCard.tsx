// SPDX-License-Identifier: Apache-2.0
// A real room on the map: you knock, and the person who opened it answers. A yes hands this browser
// a one-use invitation; a no is told plainly, and only to you.
import { useEffect, useState } from "react";
import { HostError, knockAt, readKnock } from "../genesis/api";
import type { Room } from "./rooms";
import "../forming/forming.css";

type State = "idle" | "waiting" | "no" | "failed";
type Ticket = { knock: string; secret: string };

const ASK_EVERY_MS = 2000;

/** The ticket survives leaving this pin or reloading, so a yes given later still arrives. */
function stored(room: string): Ticket | null {
  try {
    const raw = globalThis.sessionStorage?.getItem(`ck.knock.${room}`);
    return raw ? (JSON.parse(raw) as Ticket) : null;
  } catch {
    return null;
  }
}

function keep(room: string, ticket: Ticket | null) {
  try {
    const key = `ck.knock.${room}`;
    if (ticket) globalThis.sessionStorage?.setItem(key, JSON.stringify(ticket));
    else globalThis.sessionStorage?.removeItem(key);
  } catch {
    // Without storage the knock lasts as long as this card.
  }
}

export function KnockCard({ room, onJoin }: { room: Room; onJoin: (secret: string) => void }) {
  const [ticket, setTicket] = useState<Ticket | null>(() => stored(room.id));
  const [state, setState] = useState<State>(() => (stored(room.id) ? "waiting" : "idle"));
  useEffect(() => {
    if (!ticket) return;
    const timer = window.setInterval(async () => {
      try {
        const reply = await readKnock(room.id, ticket.knock, ticket.secret);
        if (reply.state === "yes" && reply.invitation) {
          window.clearInterval(timer);
          keep(room.id, null);
          onJoin(reply.invitation);
        } else if (reply.state === "no") {
          window.clearInterval(timer);
          keep(room.id, null);
          setState("no");
        }
      } catch (e) {
        // A dropped connection or a busy host passes; only a refusal ends the wait.
        if (e instanceof HostError && [403, 404].includes(e.status)) {
          window.clearInterval(timer);
          keep(room.id, null);
          setState("failed");
        }
      }
    }, ASK_EVERY_MS);
    return () => window.clearInterval(timer);
  }, [ticket, room.id, onJoin]);
  return (
    <div className="ld-knock" role="status">
      <b>{room.goal}</b>
      {state === "idle" && (
        <>
          <span>
            {room.filled} of {room.seats} seats. The person who opened it decides who comes in.
          </span>
          <button
            type="button"
            className="ld-knock-go"
            onClick={async () => {
              try {
                const made = await knockAt(room.id);
                keep(room.id, made);
                setTicket(made);
                setState("waiting");
              } catch {
                setState("failed");
              }
            }}
          >
            Knock
          </button>
        </>
      )}
      {state === "waiting" && <span>You knocked. Waiting for an answer.</span>}
      {state === "no" && <span>They said no this time.</span>}
      {state === "failed" && <span>This room isn't taking knocks right now.</span>}
    </div>
  );
}
