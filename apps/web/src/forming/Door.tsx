// SPDX-License-Identifier: Apache-2.0
// The Door: the room's QR and a code you can say out loud, while seats fill. Everything shown comes
// from the host; the page asks again every two seconds, so a new seat shows within that time.
import { useEffect, useState } from "react";
import { RoomQr } from "../door/QrCard";
import {
  type AgentHome,
  answerKnock,
  type DoorState,
  invite,
  readDoor,
  stopDoor,
} from "../genesis/api";
import { PublicNav } from "../landing/PublicNav";
import "../genesis/genesis.css";
import "../door/door.css";
import "../landing/landing.css";
import "./forming.css";

const ASK_EVERY_MS = 2000;
const SHOWN = 4;

const HOME: Record<AgentHome, string> = {
  hosted: "Muse, here in the browser",
  whatsapp: "WhatsApp",
  mcp: "Their assistant, by MCP",
  a2a: "Their own agent, A2A card",
};

/** The agent's orbit around its person. The dash pattern says where the agent lives. */
export function OrbitToken({ home, arriving = false }: { home: AgentHome; arriving?: boolean }) {
  return (
    <svg
      className="fm-token"
      data-home={home}
      data-arriving={arriving}
      width="36"
      height="36"
      viewBox="0 0 48 48"
      aria-hidden="true"
    >
      <circle className="fm-orb" cx="24" cy="24" r="17" />
      <g className="fm-sat">
        <circle cx="24" cy="7" r="3.4" />
      </g>
      <circle className="fm-me" cx="24" cy="24" r="6.5" />
    </svg>
  );
}

function closes(iso: string): string {
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return "the deadline";
  return when.toLocaleString(undefined, {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function whatsappLink(door: DoorState): string {
  return `https://wa.me/?text=${encodeURIComponent(`${door.goal} ${door.link}`)}`;
}

export function Door({
  token,
  first,
  onEnter,
}: {
  token: string;
  /** What opening the room already returned, so the first paint needs no wait. */
  first?: DoorState;
  onEnter: () => void;
}) {
  const [door, setDoor] = useState<DoorState | null>(first ?? null);
  const [hold, setHold] = useState(false);
  const [note, setNote] = useState("");
  const [lost, setLost] = useState(false);
  useEffect(() => {
    let live = true;
    const ask = async () => {
      try {
        const next = await readDoor(token);
        if (live) {
          setDoor(next);
          setLost(false);
        }
      } catch {
        if (live) setLost(true);
      }
    };
    void ask();
    const timer = window.setInterval(ask, ASK_EVERY_MS);
    return () => {
      live = false;
      window.clearInterval(timer);
    };
  }, [token]);
  const copy = async (text: string, done: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setNote(done);
    } catch {
      setNote("This browser wouldn't copy it.");
    }
  };
  const nav = <PublicNav onJoin={() => {}} ways={false} />;
  if (!door) {
    return (
      <div className="ld fm-door-page">
        {nav}
        <main className="fm-door">
          <p className="ld-sub" role="status">
            {lost ? "The host could not be reached." : "Opening the Door…"}
          </p>
        </main>
      </div>
    );
  }
  const filled = Math.min(door.filled, door.seats);
  const newest = door.arrivals[0]?.at;
  return (
    <div className="ld fm-door-page">
      {nav}
      <main className="fm-door">
        <div className="fm-door-grid" data-hold={hold}>
          <div className="fm-door-qr">
            <RoomQr link={door.link} seats={door.seats} taken={filled} />
          </div>
          <div className="fm-door-side">
            {!hold && (
              <p className="ld-eyebrow">
                {door.stopped ? "Code stopped" : "Hold this up, or say it"}
              </p>
            )}
            <div className="fm-code" data-stopped={door.stopped}>
              <span className="sr-only">Room code </span>
              {door.code}
            </div>
            <p className="fm-door-goal">{door.goal}</p>
            {hold ? (
              <div className="fm-door-actions">
                <button type="button" className="fm-btn" data-solid onClick={() => setHold(false)}>
                  Done
                </button>
              </div>
            ) : (
              <>
                <p className="ld-sub fm-door-sub">
                  {door.stopped
                    ? "Nobody new can use this code. People already seated stay."
                    : `No app needed. Any phone camera works. The code lets people in until ${closes(door.closes_at)}, or until you stop it.`}
                </p>
                <div className="fm-door-actions">
                  <button type="button" className="fm-btn" data-solid onClick={() => setHold(true)}>
                    Hold up
                  </button>
                  <button
                    type="button"
                    className="fm-btn"
                    onClick={() => copy(door.link, "Link copied.")}
                  >
                    Copy link
                  </button>
                  <a
                    className="fm-btn"
                    href={whatsappLink(door)}
                    target="_blank"
                    rel="noreferrer noopener"
                  >
                    WhatsApp
                  </a>
                  <button
                    type="button"
                    className="fm-btn"
                    onClick={async () => {
                      try {
                        const made = await invite(token, "member");
                        const link = made.invitations[0]?.link;
                        if (link) await copy(link, "A one-use link for one person is copied.");
                      } catch {
                        setNote("The host wouldn't make that link.");
                      }
                    }}
                  >
                    Seat for someone
                  </button>
                  {!door.stopped && (
                    <button
                      type="button"
                      className="fm-btn"
                      onClick={async () => {
                        try {
                          setDoor(await stopDoor(token));
                        } catch {
                          setNote("The host wouldn't stop the code.");
                        }
                      }}
                    >
                      Stop this code
                    </button>
                  )}
                </div>
                {note && (
                  <p className="fm-door-note" role="status">
                    {note}
                  </p>
                )}
                <section className="fm-panel" aria-label="Who has arrived" aria-live="polite">
                  <div className="fm-panel-head">
                    <b>
                      {filled} of {door.seats} seats
                    </b>
                    <span>{lost ? "Reconnecting…" : "Seats fill as people arrive"}</span>
                  </div>
                  <ul className="fm-arrivals">
                    {door.arrivals.slice(0, SHOWN).map((a) => (
                      <li key={a.participant}>
                        <OrbitToken home={a.home} arriving={a.at === newest} />
                        <span>
                          <b>{a.label}</b>
                          <small>{HOME[a.home]}</small>
                        </span>
                      </li>
                    ))}
                  </ul>
                  {door.knocks.slice(0, 1).map((k) => (
                    <div key={k.id} className="fm-knock">
                      <span>Someone on the map knocked.</span>
                      <button
                        type="button"
                        data-yes
                        onClick={async () => setDoor(await answerKnock(token, k.id, "yes"))}
                      >
                        Let in
                      </button>
                      <button
                        type="button"
                        onClick={async () => setDoor(await answerKnock(token, k.id, "no"))}
                      >
                        Say no
                      </button>
                    </div>
                  ))}
                </section>
                <div className="fm-door-actions">
                  <button type="button" className="fm-btn" data-solid onClick={onEnter}>
                    Enter the room
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
