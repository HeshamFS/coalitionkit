// SPDX-License-Identifier: Apache-2.0
import { Action, Badge, list, num, obj, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f10.css";

export function MintedAgentCard({ p, send }: { p: Props; send: Send }) {
  const agent = obj(p.agent);
  return (
    <>
      <div className="row">
        <span className="av av-lg av-sq s3 presence">{text(agent.name).slice(0, 1)}</span>
        <div className="col grow f10-agent-heading">
          <b>{text(agent.name)}</b>
          <span className="st">
            {text(agent.created)} · {text(agent.version)}
          </span>
        </div>
        <Badge>minted · {text(agent.runtime)}</Badge>
      </div>
      <div className="g2 f10-readings">
        {rows(p.readings).map((r) => (
          <div className="stage" key={text(r.name)}>
            <span className="st">{text(r.name)}</span>
            <span className="answer">
              {num(r.value).toLocaleString("fr-FR")} {text(r.unit)}
            </span>
            {r.live ? (
              <Badge tone="measured">live</Badge>
            ) : (
              <span className="st">{text(r.action)}</span>
            )}
          </div>
        ))}
      </div>
      <div className="row small">
        <span>Tools: {list(p.tools).map(text).join(", ")}</span>
        <button
          type="button"
          className="f10-link h-right"
          onClick={() => send("agent.logs", { agent: p.agent })}
        >
          Logs
        </button>
      </div>
      {p.health !== "live" && (
        <div className="row">
          <Action
            label="Take offline"
            event="agent.offline"
            send={send}
            data={{ agent: p.agent }}
          />
          <Action label="Re-mint" event="agent.remint" send={send} data={{ agent: p.agent }} />
        </div>
      )}
    </>
  );
}
