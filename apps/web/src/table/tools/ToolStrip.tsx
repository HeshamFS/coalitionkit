// SPDX-License-Identifier: Apache-2.0
// "What the agents are doing": the newest tool calls as one live strip, and every recorded call as
// a catalog ToolCall card behind "All calls". Each line is what the host recorded in a
// `coalition.tool` event; nothing here is made up on the screen, and nothing private ever is,
// because the host never records it.
import { useState } from "react";
import { ToolCall } from "../../components/f03/views";
import type { Room } from "../room";
import { duration, seatName, type ToolCallItem, toolWords } from "./tools";
import "./tools.css";

const SHOWN = 3;
const quiet = () => undefined;

function Mark({ status }: { status: ToolCallItem["status"] }) {
  if (status === "started") return <span className="tk-run" role="img" aria-label="running" />;
  return (
    <span className="tk-mark" data-failed={status === "failed"} role="img" aria-label={status}>
      {status === "failed" ? "!" : "✓"}
    </span>
  );
}

function Line({ call, room }: { call: ToolCallItem; room: Room }) {
  const words = toolWords(call.tool);
  return (
    <li className="tk-line" data-status={call.status} data-tool={call.tool}>
      <Mark status={call.status} />
      <b className="tk-who">{seatName(room.seats, call.seat)}</b>
      <code className="tk-tool" title={words.family}>
        {call.tool}
      </code>
      <span className="tk-args">{call.args || words.name}</span>
      <span className="tk-took">
        {call.status === "started" ? "running" : duration(call.ms)}
        {call.status !== "started" && call.result ? ` · ${call.result}` : ""}
      </span>
    </li>
  );
}

/** The newest calls, running ones first, then the most recent finished ones. */
export function newestCalls(tools: ToolCallItem[], count = SHOWN): ToolCallItem[] {
  const running = tools.filter((t) => t.status === "started");
  const rest = tools.filter((t) => t.status !== "started");
  return [...running.slice(-count), ...rest.slice(-count)].slice(0, count);
}

export function ToolStrip({ room }: { room: Room }) {
  const [open, setOpen] = useState(false);
  const tools = room.tools ?? [];
  if (tools.length === 0 || room.phase === "ended") return null;
  const live = tools.filter((t) => t.status === "started").length;
  return (
    <section className="tk-strip" aria-label="What the agents are doing">
      <header className="tk-head">
        <span className="tk-title">What the agents are doing</span>
        <span className="tk-count">
          {live > 0 ? `${live} running · ` : ""}
          {tools.length} calls
        </span>
        <button type="button" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "Hide calls" : "All calls"}
        </button>
      </header>
      <ol className="tk-lines" aria-live="polite">
        {newestCalls(tools).map((call) => (
          <Line key={call.id} call={call} room={room} />
        ))}
      </ol>
      {open && (
        <div className="tk-cards">
          {[...tools].reverse().map((call) => (
            <ToolCall
              key={call.id}
              send={quiet}
              p={{
                tool: `${seatName(room.seats, call.seat)} · ${call.tool}`,
                state: call.status === "started" ? "running" : call.status,
                duration: { value: Math.round(call.ms / 100) / 10 },
                failure: call.status === "failed" ? call.result : "",
                summary: call.result ? `${call.args} → ${call.result}` : call.args,
                provenance: `${call.agent} · seq ${call.seq}`,
                args: { agent: call.agent, args: call.args, result: call.result, refs: call.refs },
              }}
            />
          ))}
        </div>
      )}
    </section>
  );
}
