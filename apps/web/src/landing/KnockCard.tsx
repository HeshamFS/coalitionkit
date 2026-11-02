// SPDX-License-Identifier: Apache-2.0
// A real room on the map: you knock, and the person who opened it answers. A yes hands this browser
// a one-use invitation; a no is told plainly, and only to you.
import { useEffect, useState } from "react";
import { knockAt, readKnock } from "../genesis/api";
import type { Room } from "./rooms";
import "../forming/forming.css";

type State = "idle" | "waiting" | "no" | "failed";

const ASK_EVERY_MS = 2000;

export function KnockCard({ room, onJoin }: { room: Room; onJoin: (secret: string) => void }) {
  const [state, setState] = useState<State>("idle");
  const [ticket, setTicket] = useState<{ knock: string; secret: string } | null>(null);
  useEffect(() => {
    if (!ticket) return;
    const timer = window.setInterval(async () => {
      try {
        const reply = await readKnock(room.id, ticket.knock, ticket.secret);
        if (reply.state === "yes" && reply.invitation) {
          window.clearInterval(timer);
          onJoin(reply.invitation);
        } else if (reply.state === "no") {
          window.clearInterval(timer);
          setState("no");
        }
      } catch {
        window.clearInterval(timer);
        setState("failed");
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
                setTicket(await knockAt(room.id));
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
