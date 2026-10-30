// SPDX-License-Identifier: Apache-2.0
import { type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

export function ConnectionStatus({ p, send }: { p: Props; send: Send }) {
  const feed = text(p.feed) || "offline";
  return (
    <button
      type="button"
      className={`dock f09-connection f09-${feed}`}
      onClick={() => send("feed.reconnect", { run: p.run })}
      disabled={feed === "live"}
      aria-label={feed === "live" ? "Live connection" : "Reconnect"}
    >
      <span
        className={feed === "live" ? "live-dot pulse" : feed === "offline" ? "pin" : "spinner"}
      />
      <b>{feed === "live" ? "Live" : feed === "offline" ? "Offline" : "Reconnecting"}</b>
      {feed === "live"
        ? ` · feed run ${text(p.run)} · ${text(p.latencyMs)} ms`
        : feed === "offline"
          ? " · showing the last good view"
          : " · new run, fresh snapshot"}
    </button>
  );
}
