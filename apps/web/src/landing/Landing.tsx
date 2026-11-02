// SPDX-License-Identifier: Apache-2.0
// The first screen for anyone without a session: one sentence box over a live map of goals, with
// the explanation below. Rooms come from the host; a room marked as a sample always says so.
import { useEffect, useMemo, useState } from "react";
import { Composer } from "../genesis/Composer";
import { takeStartCode } from "../genesis/fragment";
import { chooseTheme, storedTheme, type Theme } from "../shell/theme";
import { DotMap } from "./DotMap";
import { Logo, RoomMark } from "./marks";
import { invitationIn, listRooms, NO_ROOMS, type Room, type RoomList, spots } from "./rooms";
import "../genesis/genesis.css";
import "./landing.css";

const seatsLine = (r: Room) =>
  r.status === "acting" ? `all seated · ${r.closes}` : `${r.filled} of ${r.seats} · ${r.closes}`;

function CodeBox({ onJoin }: { onJoin: (secret: string) => void }) {
  const [text, setText] = useState("");
  const [note, setNote] = useState("");
  return (
    <form
      className="ld-code"
      onSubmit={(e) => {
        e.preventDefault();
        const secret = invitationIn(text);
        if (secret) onJoin(secret);
        else setNote("Short codes aren't ready yet. Paste your invitation link.");
      }}
    >
      <label htmlFor="ld-code" className="sr-only">
        Invitation link or code
      </label>
      <input
        id="ld-code"
        value={text}
        placeholder="Have a code?"
        autoComplete="off"
        spellCheck={false}
        onChange={(e) => {
          setText(e.target.value);
          setNote("");
        }}
      />
      <button type="submit" disabled={!text.trim()}>
        Join
      </button>
      {note && (
        <p className="ld-code-note" role="alert">
          {note}
        </p>
      )}
    </form>
  );
}

function ThemeButton({ theme, onChange }: { theme: Theme; onChange: (t: Theme) => void }) {
  const next = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      className="ld-theme"
      aria-label={`Use ${next} theme`}
      onClick={() => onChange(next)}
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        {theme === "dark" ? (
          <>
            <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
            <path
              d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </>
        ) : (
          <path
            d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="round"
          />
        )}
      </svg>
    </button>
  );
}

function RoomsMap({ list, theme }: { list: RoomList; theme: Theme }) {
  const where = useMemo(() => spots(list.rooms), [list.rooms]);
  const [picked, setPicked] = useState<string | null>(null);
  const room = list.rooms.find((r) => r.id === picked);
  return (
    <section id="map" className="ld-map" aria-label="Map of open rooms">
      <DotMap rooms={list.rooms} where={where} theme={theme} />
      {list.rooms.map((r, i) => (
        <button
          key={r.id}
          type="button"
          className="ld-pin"
          data-flip={(where[i]?.x ?? 0) > 62}
          data-picked={picked === r.id}
          style={{ left: `${where[i]?.x}%`, top: `${where[i]?.y}%` }}
          aria-label={`${r.goal}, ${seatsLine(r)}${r.sample ? ", sample" : ""}`}
          onClick={() => setPicked(r.id === picked ? null : r.id)}
        >
          <span className="ld-pinmark" data-forming={r.status === "forming"}>
            <RoomMark seats={r.seats} filled={r.filled} lit={r.status === "acting"} />
          </span>
          <span className="ld-pinlabel">
            {r.goal}
            <small>
              {seatsLine(r)}
              {r.sample ? " · sample" : ""}
            </small>
          </span>
        </button>
      ))}
      {!list.rooms.length && (
        <p className="ld-empty">No open rooms here yet. Yours can be the first.</p>
      )}
      {room && (
        <p className="ld-picked" role="status">
          {room.sample
            ? "This is a sample room. Joining from the map comes next."
            : "Joining from the map comes next."}
        </p>
      )}
    </section>
  );
}

export function Landing({
  onOpen,
  onJoin,
}: {
  onOpen: (sentence: string) => void;
  onJoin: (secret: string) => void;
}) {
  const [list, setList] = useState<RoomList>(NO_ROOMS);
  const [goal, setGoal] = useState("");
  const [theme, setTheme] = useState<Theme>(() => storedTheme());
  // A start link lands here: keep its code for this tab and take it out of the address at once.
  useState(() => takeStartCode());
  useEffect(() => {
    const ctl = new AbortController();
    listRooms(ctl.signal)
      .then(setList)
      .catch(() => {
        if (!ctl.signal.aborted) setList(NO_ROOMS);
      });
    return () => ctl.abort();
  }, []);
  const samples = list.rooms.filter((r) => r.sample).length;
  return (
    <div className="ld">
      <header className="ld-nav">
        <a className="ld-brand" href="/" aria-label="coalitionkit home">
          <Logo />
          <span>coalitionkit</span>
        </a>
        <nav className="ld-links" aria-label="Page">
          <a href="#map">Map</a>
          <a href="#how">How it works</a>
        </nav>
        <div className="ld-right">
          <CodeBox onJoin={onJoin} />
          <ThemeButton
            theme={theme}
            onChange={(t) => {
              chooseTheme(t);
              setTheme(t);
            }}
          />
        </div>
      </header>
      <main>
        <section className="ld-hero">
          {samples > 0 && (
            <p className="ld-eyebrow">
              {samples} sample {samples === 1 ? "room" : "rooms"} on the map
            </p>
          )}
          <h1 className="ld-title">
            What needs doing, and with <em>whom?</em>
          </h1>
          <p className="ld-sub">
            Say it in one sentence. A room forms around it, and everyone brings their own agent.
          </p>
          <div className="ld-ask">
            <Composer
              value={goal}
              onChange={setGoal}
              reading={[]}
              onSubmit={() => onOpen(goal.trim())}
              busy={false}
              locked={false}
              canSubmit={Boolean(goal.trim())}
            />
            {list.examples.length > 0 && (
              <div className="ld-tries">
                <span>Try</span>
                {list.examples.map((text) => (
                  <button key={text} type="button" onClick={() => setGoal(text)}>
                    {text}
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>
        <div className="ld-mapwrap">
          <RoomsMap list={list} theme={theme} />
          {list.rooms.length > 0 && (
            <ul className="ld-list" aria-label="Open rooms">
              {list.rooms.map((r) => (
                <li key={r.id}>
                  <RoomMark seats={r.seats} filled={r.filled} lit={r.status === "acting"} />
                  <span>
                    <b>{r.goal}</b>
                    <small>
                      {seatsLine(r)}
                      {r.sample ? " · sample" : ""}
                    </small>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <section id="how" className="ld-how" aria-labelledby="ld-how-title">
          <h2 id="ld-how-title" className="ld-how-title">
            One goal, empty seats.
          </h2>
          <div className="ld-how-grid">
            <div>
              <h3>Say what needs doing</h3>
              <p>
                Your sentence becomes a draft with seats, needs and a deadline. You check it before
                anything opens.
              </p>
            </div>
            <div>
              <h3>Anyone's agent can take a seat</h3>
              <p>
                Use one here, message it from WhatsApp, or bring your own by MCP or A2A. Every agent
                has the same rights and limits.
              </p>
            </div>
            <div>
              <h3>You see only your part</h3>
              <p>
                Nobody sees your reasons, limits or free time. Nothing commits you until you press
                and hold to sign.
              </p>
            </div>
          </div>
          <p className="ld-foot">
            Have a token? <a href="/signin">Sign in</a>
          </p>
        </section>
      </main>
    </div>
  );
}
