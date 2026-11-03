// SPDX-License-Identifier: Apache-2.0
// Your side once the work is under way and when the room has ended: your tasks, the record check,
// the end of the room, and what stays.
import { useMemo, useState } from "react";
import { ChainView } from "../chain/ChainView";
import { chainInputFrom } from "../chain/input";
import { readConfig } from "../feed/config";
import type { CleanupCounts } from "../moments/Dissolve";
import { EndConfirm } from "../room/endCoalition";
import { beginEnd, readEnded } from "../room/ended";
import { Asks } from "./Asks";
import { problemText } from "./api";
import { useTable } from "./context";
import { needStatus } from "./needWords";
import type { MyTask } from "./room";

function Task({ task }: { task: MyTask }) {
  const { io, openResult } = useTable();
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState("");
  const done = task.status === "done";
  const mark = async () => {
    setBusy(true);
    setProblem("");
    const r = await io.done(task.task_id);
    setBusy(false);
    if (!r.ok) {
      setProblem(
        r.status === 409
          ? "Not yet: your result has to be there before you can mark this done."
          : problemText(r),
      );
    }
  };
  return (
    <li className="tb-task">
      <span>
        {task.title}
        <small>{needStatus(task.status, 0, "waiting")}</small>
      </span>
      <span className="tb-row">
        {task.result && (
          <button
            type="button"
            className="btn tb-quietbtn"
            onClick={() => openResult(task.result as string)}
          >
            See it
          </button>
        )}
        <button
          type="button"
          className="btn tb-quietbtn"
          disabled={busy || done || !task.can_mark_done}
          onClick={mark}
        >
          {done ? "Done" : busy ? "Sending…" : "Mark done"}
        </button>
      </span>
      {problem && <p role="alert">{problem}</p>}
    </li>
  );
}

/** Check the record in this browser, and end the room if you started it. */
export function Finish({ canEnd }: { canEnd: boolean }) {
  const { state, owner } = useTable();
  const [checking, setChecking] = useState(false);
  const [ending, setEnding] = useState(false);
  const log = state?.log;
  // biome-ignore lint/correctness/useExhaustiveDependencies: the input is derived from the log only
  const input = useMemo(() => chainInputFrom(state), [log]);
  return (
    <section className="tb-finish" aria-label="Finish">
      <span className="tb-tag">Check it, then end it</span>
      <p>Your browser can check every signed link itself. You do not have to trust the host.</p>
      <button type="button" className="btn tb-quietbtn" onClick={() => setChecking(!checking)}>
        {checking ? "Hide the record" : "Check the record myself"}
      </button>
      {checking && (
        <div className="tb-chain">
          <ChainView input={input} />
        </div>
      )}
      {canEnd && owner && (
        <button type="button" className="btn" onClick={() => setEnding(true)}>
          End the room
        </button>
      )}
      {ending && (
        <EndConfirm
          onCancel={() => setEnding(false)}
          onConfirm={(reason) => {
            const token = readConfig()?.token;
            setEnding(false);
            if (token) beginEnd({ token, reason });
          }}
        />
      )}
    </section>
  );
}

export function SideLive() {
  const { room } = useTable();
  const tasks = room.mine.tasks;
  const feed = room.mine.feed.slice(-4);
  return (
    <>
      <Asks />
      <h2>Your part</h2>
      {tasks.length === 0 ? (
        <p role="status">No task is yours in this plan.</p>
      ) : (
        <ul className="tb-tasks">
          {tasks.map((t) => (
            <Task key={t.task_id} task={t} />
          ))}
        </ul>
      )}
      {feed.length > 0 && (
        <div className="tb-feed" role="log" aria-label="Your agent's private feed">
          {feed.map((f) => (
            <div key={`${f.at}:${f.text}`}>{f.text}</div>
          ))}
        </div>
      )}
      <p className="tb-note">Plans change. Tell the room below what just happened.</p>
      <Finish canEnd />
    </>
  );
}

const ERASED: [keyof CleanupCounts, string, string][] = [
  ["vaults_erased", "private vault erased", "private vaults erased"],
  ["tokens_revoked", "viewer link stopped", "viewer links stopped"],
  ["tasks_closed", "open task closed", "open tasks closed"],
  ["invitations_revoked", "invitation withdrawn", "invitations withdrawn"],
];

/** What the host says it cleaned up. Only numbers it actually sent are shown. */
function Erased({ counts }: { counts: CleanupCounts }) {
  const lines = ERASED.flatMap(([key, one, many]) => {
    const n = counts[key];
    return typeof n === "number" ? [`${n} ${n === 1 ? one : many}`] : [];
  });
  if (lines.length === 0) return null;
  return (
    <>
      <span className="tb-tag">What was erased</span>
      <ul className="tb-list">
        {lines.map((l) => (
          <li key={l}>{l}</li>
        ))}
      </ul>
    </>
  );
}

export function SideEnded() {
  const { room, openResult, ending } = useTable();
  const kept = room.results.filter((r) => r.replaced_by === null);
  const base = ending?.event ?? readEnded();
  const report = ending?.report;
  const counts: CleanupCounts | undefined = report && "failed" in report ? report.done : report;
  const skills = counts?.skills_written?.length
    ? counts.skills_written
    : (base?.skills_written ?? []);
  return (
    <>
      <h2>The room has ended</h2>
      {ending?.pending && <p role="status">Ending the room for everyone…</p>}
      {ending?.refused && (
        <>
          <p role="alert" className="tb-bad">
            {ending.refused}
          </p>
          {ending.onRetry && (
            <button type="button" className="btn tb-quietbtn" onClick={ending.onRetry}>
              Try again
            </button>
          )}
        </>
      )}
      {counts && <Erased counts={counts} />}
      {skills.length > 0 && (
        <>
          <span className="tb-tag">Lessons kept, with no private data in them</span>
          <ul className="tb-list">
            {skills.map((id) => (
              <li key={id}>{counts?.lessons?.[id]?.title || id}</li>
            ))}
          </ul>
        </>
      )}
      <span className="tb-tag">What the room made</span>
      {kept.length === 0 ? (
        <p role="status">Nothing was made in this room.</p>
      ) : (
        <>
          <p>
            These results live only in this tab. Export or copy what you want now: once you leave,
            they are gone.
          </p>
          <ul className="tb-kept">
            {kept.map((r) => (
              <li key={r.id}>
                <button type="button" className="tb-linky" onClick={() => openResult(r.id)}>
                  {r.title}
                </button>
                <small>
                  from {r.sources.length} {r.sources.length === 1 ? "event" : "events"}
                </small>
              </li>
            ))}
          </ul>
        </>
      )}
      {ending ? (
        <button type="button" className="btn tb-quietbtn" onClick={ending.onLeave}>
          Leave, back to the start
        </button>
      ) : (
        <Finish canEnd={false} />
      )}
    </>
  );
}
