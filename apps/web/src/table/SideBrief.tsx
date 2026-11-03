// SPDX-License-Identifier: Apache-2.0
// Brief: your agent asks one question at a time, privately. The question is a tree the host
// composed and checked; its value is read from the surface's data model and posted to the host,
// which checks it against the question's closed shape. It goes to your vault and nowhere else.
import { A2uiSurface } from "@a2ui/react/v0_9";
import { useRef, useState } from "react";
import { problemText } from "./api";
import { useTable } from "./context";
import type { BriefItem } from "./room";
import { briefValue, useSurface } from "./useSurface";

function Question({ item, index, total }: { item: BriefItem; index: number; total: number }) {
  const { io } = useTable();
  const [sentId, setSentId] = useState("");
  const [problem, setProblem] = useState("");
  // The inputs in the tree report what the person chose as `change` and `select` actions; the
  // last value wins. A `submit` from the tree (a button, or Enter) sends it, like the control below.
  const picked = useRef<unknown>(undefined);
  const found = useSurface(item.messages, (a) => {
    if (a.context && "value" in a.context) picked.current = a.context.value;
    if (a.name === "submit") void send();
  });
  const last = index === total - 1;
  const sent = sentId === item.id;

  async function send(skip = false) {
    setProblem("");
    const value = skip ? undefined : (picked.current ?? briefValue(found?.model ?? null));
    if (!skip && value === undefined) {
      setProblem("Pick or fill in an answer first, or skip this one.");
      return;
    }
    const r = await io.brief(item.id, skip ? { skip: true } : { value });
    if (!r.ok) {
      setProblem(
        r.status === 422
          ? "That answer does not fit this question. Change it and send again."
          : problemText(r),
      );
      return;
    }
    setSentId(item.id);
  }

  return (
    <>
      <span className="tb-tag">
        Your agent asks · {index + 1} of {total}
      </span>
      <h2>{item.ask || "A question for you"}</h2>
      {item.why && <p>{item.why}</p>}
      <div className="tb-card tb-card--tall">
        {!found && (
          <div className="tb-germ">{item.component || "A question"} is being composed</div>
        )}
        {found && !found.fallback && <A2uiSurface surface={found.model} />}
        {found?.fallback && (
          <p className="tb-quiet" role="note">
            This question could not be drawn as the host designed it. You can skip it.
          </p>
        )}
      </div>
      {sent ? (
        <p role="status">Saved to your vault. Waiting for the next step.</p>
      ) : (
        <div className="tb-row">
          <button
            type="button"
            className="btn"
            disabled={!found || found.fallback}
            onClick={() => send()}
          >
            {last ? "Let the agents work" : "Next"}
          </button>
          <button type="button" className="tb-linky" onClick={() => send(true)}>
            Skip
          </button>
        </div>
      )}
      {problem && <p role="alert">{problem}</p>}
      <p className="tb-note">Stays in your vault. Your agent shares only what you agree to.</p>
    </>
  );
}

export function SideBrief() {
  const { room } = useTable();
  const items = room.mine.brief;
  const index = items.findIndex((b) => b.status === "open");
  if (items.length === 0) {
    return (
      <>
        <h2>Your agent has no questions yet</h2>
        <p role="status">It will ask here, one at a time, when it needs something only you know.</p>
      </>
    );
  }
  const current = items[index];
  if (!current) {
    return (
      <>
        <h2>All answered</h2>
        <p role="status">
          Your agent has what it needs. It will start as soon as the others are ready.
        </p>
      </>
    );
  }
  return <Question key={current.id} item={current} index={index} total={items.length} />;
}
