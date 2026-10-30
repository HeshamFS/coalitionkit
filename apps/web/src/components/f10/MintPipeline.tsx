// SPDX-License-Identifier: Apache-2.0
import { Action, Badge, Bar, list, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f10.css";

export function MintPipeline({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <div className="f10-stages">
        {rows(p.stages).map((s, i) => (
          <div className="card" key={text(s.name) || `${i}`}>
            <Badge tone={s.state === "done" ? "measured" : "estimate"}>{text(s.state)}</Badge>
            <b>{text(s.name)}</b>
            <span className="small">{text(s.detail)}</span>
            <span className="st">{text(s.took)} s</span>
            {list(s.artifacts).map((a) => (
              <Action
                key={text(a)}
                label={`Open ${text(a)}`}
                event="stage.open"
                send={send}
                data={{ artifact: a }}
              />
            ))}
          </div>
        ))}
      </div>
      <Bar
        value={
          rows(p.stages).filter((s) => s.state === "done").length /
          Math.max(1, rows(p.stages).length)
        }
      />
      <div className="row small">
        <span>Elapsed {text(p.elapsed)} s</span>
        <span className="h-right">{text(p.cost)}</span>
      </div>
    </>
  );
}
