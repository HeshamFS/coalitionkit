// SPDX-License-Identifier: Apache-2.0
import { Action, type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

export function ConnectionStatus({ p, send }: { p: Props; send: Send }) {
  return (
    <div className="row">
      <span className={p.feed === "live" ? "live-dot pulse" : "spinner"} />
      <b>{text(p.feed)}</b>
      <span className="st">{text(p.latencyMs)} ms</span>
      {p.feed !== "live" && (
        <Action label="Reconnect" event="feed.reconnect" send={send} data={{ run: p.run }} />
      )}
    </div>
  );
}
