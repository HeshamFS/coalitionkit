// SPDX-License-Identifier: Apache-2.0
// Your side once the work is under way and when the room has ended: your tasks, the record check,
// the end of the room, and what stays.
import { useMemo, useState } from "react";
import { ChainView } from "../chain/ChainView";
import { chainInputFrom } from "../chain/input";
import { readConfig } from "../feed/config";
import { EndConfirm } from "../room/endCoalition";
import { beginEnd, readEnded } from "../room/ended";
import { Asks } from "./Asks";
import { problemText } from "./api";
import { useTable } from "./context";
import { humanStatus } from "./phase";
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
        <small>{humanStatus(task.status) || "waiting"}</small>
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

export function SideEnded() {
  const { room, openResult } = useTable();
  const kept = room.results.filter((r) => r.replaced_by === null);
  const lessons = readEnded()?.skills_written.length ?? 0;
  return (
    <>
      <h2>What is left</h2>
      {kept.length === 0 ? (
        <p role="status">Nothing was made in this room.</p>
      ) : (
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
      )}
      {lessons > 0 && (
        <p>
          {lessons} {lessons === 1 ? "lesson" : "lessons"} written as{" "}
          {lessons === 1 ? "a skill" : "skills"}, with no private data in{" "}
          {lessons === 1 ? "it" : "them"}.
        </p>
      )}
      <Finish canEnd={false} />
    </>
  );
}
