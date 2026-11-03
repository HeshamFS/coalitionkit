// SPDX-License-Identifier: Apache-2.0
// Brief: your agent asks one question at a time, privately. The question is a tree the host
// composed and checked; its value is read from the surface's data model and posted to the host,
// which checks it against the question's closed shape. It goes to your vault and nowhere else.
import { A2uiSurface } from "@a2ui/react/v0_9";
import { useRef, useState } from "react";
import type { Surface } from "../feed/surfaces";
import { problemText } from "./api";
import { useTable } from "./context";
import type { BriefItem } from "./room";
import { useSurface } from "./useSurface";

/** `{value, event_ref}` numbers go to the host as the plain value. */
export const unwrap = (v: unknown): unknown =>
  v !== null && typeof v === "object" && !Array.isArray(v) && "value" in v && "event_ref" in v
    ? (v as { value: unknown }).value
    : v;

function Question({ item, index, total }: { item: BriefItem; index: number; total: number }) {
  const { io } = useTable();
  const [sentId, setSentId] = useState("");
  const [problem, setProblem] = useState("");
  const model = useRef<Surface | null>(null);
  // The inputs report the person's choice as `change` and `select` actions; it goes to `/answer` of
  // this question's surface. The tree's own Send button carries `room.brief` with the question id
  // and the value at `/answer`, and that is what is posted.
  const found = useSurface(item.messages, (a) => {
    const ctx = (a.context ?? {}) as Record<string, unknown>;
    if ((a.name === "change" || a.name === "select") && "value" in ctx) {
      model.current?.dataModel.set("/answer", unwrap(ctx.value));
    }
    if (a.name === "room.brief")
      void send({ value: unwrap(ctx.value) }, String(ctx.question_id ?? item.id));
  });
  model.current = found?.model ?? null;
  const sent = sentId === item.id;

  async function send(answer: { value: unknown } | { skip: true }, id = item.id) {
    setProblem("");
    if ("value" in answer && answer.value === undefined) {
      setProblem("Pick or fill in an answer first, or skip this one.");
      return;
    }
    const r = await io.brief(id, answer);
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
    <div className="tb-brief">
      <span className="tb-tag">
        Your agent asks · {index + 1} of {total}
      </span>
      {found?.fallback && <h2>{item.ask || "A question for you"}</h2>}
      {!found && (
        <div className="tb-card tb-card--tall">
          <div className="tb-germ">{item.component || "A question"} is being composed</div>
        </div>
      )}
      {found && !found.fallback && <A2uiSurface surface={found.model} />}
      {found?.fallback && (
        <p className="tb-quiet" role="note">
          This question could not be drawn as the host designed it. You can skip it.
        </p>
      )}
      {sent ? (
        <p role="status">Saved to your vault. Waiting for the next step.</p>
      ) : (
        <button type="button" className="tb-linky" onClick={() => send({ skip: true })}>
          Skip this one
        </button>
      )}
      {problem && <p role="alert">{problem}</p>}
      <p className="tb-note">Stays in your vault. Your agent shares only what you agree to.</p>
    </div>
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
