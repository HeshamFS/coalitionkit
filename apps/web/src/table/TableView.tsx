// SPDX-License-Identifier: Apache-2.0
// The Table, from data it is handed: the room, the viewer state, the open requests and the ways
// to talk to the host. The live screen (Table.tsx) hands it the real ones; the gallery hands it a
// scripted room and local stand-ins, so what you see there is this same screen.
import { useEffect, useRef, useState } from "react";
import type { ConsentAcknowledgement } from "../components/f08/ConsentSeal";
import type { Answer } from "../feed/actions";
import type { OpenRequest } from "../feed/agent";
import type { ViewerState } from "../feed/delta";
import { derivePlans, visibleRequests } from "../feed/derive";
import type { AnswerOutcome } from "../feed/useFeed";
import { sheetFor } from "../room/consentSheet";
import { SignedNotice } from "../room/signed";
import type { RoomIo } from "./api";
import { Band } from "./Band";
import { type Ending, type Said, TableContext, type TableCtx } from "./context";
import { COMPACT, WIDE } from "./geometry";
import { PlanCards } from "./PlanCards";
import { layoutClass } from "./phase";
import { Moments, Say, SayNote } from "./Rail";
import { ResultDialog, type Shown, shownFor } from "./ResultDialog";
import type { Room } from "./room";
import { Side } from "./Side";
import { Stage } from "./Stage";
import { Tray, trayVisible } from "./Tray";
import "./table.css";
import "./stage.css";
import "./beams.css";
import "./plans.css";
import "./side.css";
import "./tray.css";
import "../styles/room.css";

export type TableViewProps = {
  room: Room;
  state: ViewerState | null;
  requests: OpenRequest[];
  focus: string | null;
  setFocus: (id: string | null) => void;
  answer: (a: Answer) => Promise<ConsentAcknowledgement | undefined>;
  outcome: (a: Answer, quiet?: boolean) => Promise<AnswerOutcome>;
  io: RoomIo;
  phone: boolean;
  owner: boolean;
  status: "connecting" | "live" | "reconnecting";
  refusal?: string | null;
  onSignOut?: () => void;
  /** Set when the feed has closed and this screen is showing how the room ended. */
  ending?: Ending;
};

type Receipt = { question: string; seq: number; signature: string; phase: string };

function Receipts({
  list,
  phase,
  banner,
  onDone,
}: {
  list: Receipt[];
  phase: string;
  banner: boolean;
  onDone: () => void;
}) {
  const last = list.at(-1);
  if (!last) return null;
  // The loud banner lasts only while the room is still in the phase of the yes. After that the
  // receipt stays, quietly, in the list.
  const fresh = banner && last.phase === phase;
  return (
    <>
      {fresh && (
        <SignedNotice
          question={last.question}
          seq={last.seq}
          signature={last.signature}
          onClose={onDone}
        />
      )}
      <details className="tb-receipts">
        <summary>Your signatures ({list.length})</summary>
        <ul>
          {list.map((r) => (
            <li key={`${r.seq}:${r.signature}`}>
              {r.question.replace(/\?$/, "")} · seq {r.seq} · sig {r.signature.slice(0, 4)}…
              {r.signature.slice(-2)}
            </li>
          ))}
        </ul>
      </details>
    </>
  );
}
function Panes({
  phone,
  waiting,
  side,
  table,
}: {
  phone: boolean;
  waiting: boolean;
  side: React.ReactNode;
  table: React.ReactNode;
}) {
  const track = useRef<HTMLDivElement>(null);
  const [at, setAt] = useState(0);
  if (!phone) {
    return (
      <div className="tb-grid">
        {table}
        {side}
      </div>
    );
  }
  const go = (i: number) => {
    const el = track.current;
    if (!el) return;
    el.scrollTo?.({ left: i * el.clientWidth, behavior: "smooth" });
    setAt(i);
  };
  return (
    <>
      <fieldset className="tb-switch">
        <legend className="tb-sr">Which part to show</legend>
        <button type="button" aria-pressed={at === 0} onClick={() => go(0)}>
          Your side{waiting && at !== 0 ? <i role="img" aria-label="waiting for your yes" /> : null}
        </button>
        <button type="button" aria-pressed={at === 1} onClick={() => go(1)}>
          The table
        </button>
      </fieldset>
      <div
        className="tb-panes"
        ref={track}
        onScroll={(e) => {
          const el = e.currentTarget;
          setAt(Math.round(el.scrollLeft / Math.max(1, el.clientWidth)));
        }}
      >
        <div className="tb-pane">{side}</div>
        <div className="tb-pane">{table}</div>
      </div>
    </>
  );
}

export function TableView(props: TableViewProps) {
  const { room, state, answer, phone, status } = props;
  const [viewing, setViewing] = useState<string | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [opened, setOpened] = useState<string | null>(null);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [banner, setBanner] = useState(true);
  const [said, setSaid] = useState<Said | null>(null);
  const [hidden, setHidden] = useState("");
  // The host leaves out a task whose commitment is also waiting: one yes closes both, so a second
  // consent for it must not be shown.
  const theirs = room.mine.asks;
  const requests = theirs
    ? props.requests.filter((r) => r.kind !== "task" || theirs.some((a) => a.id === r.subjectId))
    : props.requests;
  const asks = visibleRequests(state, requests);
  const plans = derivePlans(state);
  const looking = room.seats.find((s) => s.seat === viewing) ?? null;
  const shown: Shown | null = (() => {
    const r = room.results.find((x) => x.id === opened);
    return r ? shownFor(room, state, r) : null;
  })();
  useEffect(() => {
    if (room.phase !== "decide") setPicked(null);
  }, [room.phase]);

  const note = (a: Answer, ack: ConsentAcknowledgement | undefined) => {
    const req = requests.find((r) => r.id === a.interrupt_id);
    if (ack && a.consent) {
      const question = req ? sheetFor(req, state).question : "Your yes";
      setReceipts((list) => [...list, { question, ...ack, phase: room.phase }]);
      setBanner(true);
    }
  };
  const record = async (a: Answer) => {
    const ack = await answer(a);
    note(a, ack);
    return ack;
  };
  const recordOutcome = async (a: Answer, quiet?: boolean) => {
    const done = await props.outcome(a, quiet);
    note(a, done.ok ? done.ack : undefined);
    return done;
  };
  const ctx: TableCtx = {
    room,
    state,
    requests,
    asks,
    focus: props.focus,
    setFocus: props.setFocus,
    answer: record,
    outcome: recordOutcome,
    io: props.io,
    phone,
    owner: props.owner,
    viewing,
    openResult: setOpened,
    said,
    setSaid,
    ending: props.ending,
  };
  const pick = (id: string) => setPicked(id);
  const cards = (
    <PlanCards
      plans={plans}
      room={room}
      selected={picked}
      signed={new Set()}
      onPick={pick}
      placement="strip"
    />
  );
  const stage = (
    <Stage
      room={room}
      layout={phone ? COMPACT : WIDE}
      viewing={viewing}
      onSeat={(seat) => {
        const s = room.seats.find((x) => x.seat === seat);
        setViewing(s && !s.you && viewing !== seat ? seat : null);
      }}
      plans={cards}
      plansCount={plans.length}
      waiting={asks.length > 0}
      tray={trayVisible(room) ? <Tray room={room} onOpen={setOpened} /> : null}
    />
  );
  const refusal = props.refusal && props.refusal !== hidden ? props.refusal : null;
  return (
    <TableContext.Provider value={ctx}>
      <div className={`tb ${layoutClass(phone)}`} data-lights={room.lights}>
        <Band room={room} state={state} onSignOut={props.onSignOut} />
        {status === "reconnecting" && (
          <p className="tb-notice" role="status">
            <span>
              The connection to the host dropped. This is the last state it sent; it updates when
              the host is back.
            </span>
          </p>
        )}
        {refusal && (
          <p
            className="tb-notice"
            role="alert"
            data-bad="true"
            style={{ top: status === "reconnecting" ? 74 : 10 }}
          >
            <span>The host did not take that answer: {refusal}</span>
            <button type="button" onClick={() => setHidden(refusal)}>
              Dismiss
            </button>
          </p>
        )}
        <Panes
          phone={phone}
          waiting={asks.length > 0}
          side={
            <div className="tb-sidecol">
              <SayNote />
              <Receipts
                list={receipts}
                phase={room.phase}
                banner={banner}
                onDone={() => setBanner(false)}
              />
              <Side
                looking={looking}
                onBack={() => setViewing(null)}
                plans={plans}
                selected={picked}
                onPick={pick}
              />
            </div>
          }
          table={stage}
        />
        <footer className="tb-rail">
          <Moments />
          <Say />
        </footer>
        {shown && <ResultDialog shown={shown} onClose={() => setOpened(null)} />}
      </div>
    </TableContext.Provider>
  );
}
