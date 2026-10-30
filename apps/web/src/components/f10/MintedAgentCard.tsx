// SPDX-License-Identifier: Apache-2.0
import { Action, Badge, obj, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f10.css";

export function MintedAgentCard({ p, send }: { p: Props; send: Send }) {
  {
    const a = obj(p.agent);
    return (
      <>
        <div className="row">
          <span className="av av-lg av-sq s3">{text(a.name).slice(0, 1)}</span>
          <div className="grow">
            <b>{text(a.name)}</b>
            <div className="st">
              {text(a.version)} · {text(a.owner)}
            </div>
          </div>
          <Badge>
            {text(p.health)} · {text(a.runtime)}
          </Badge>
        </div>
        <div className="g2">
          {rows(p.readings).map((r, i) => (
            <div className="card card-2" key={text(r.name) || `${i}`}>
              <span className="st">{text(r.name)}</span>
              <b className="answer">
                {text(r.value)} {text(r.unit)}
              </b>
            </div>
          ))}
        </div>
        <span className="small">Tools: {text(p.tools)}</span>
        <div className="row wrap">
          <Action label="Logs" event="agent.logs" send={send} data={{ agent: p.agent }} />
          <Action
            label="Take offline"
            event="agent.offline"
            send={send}
            data={{ agent: p.agent }}
          />
          <Action label="Re-mint" event="agent.remint" send={send} data={{ agent: p.agent }} />
        </div>
      </>
    );
  }
}
