// SPDX-License-Identifier: Apache-2.0
import { Action, Badge, Fields, obj, type Props, type Send, Table, text } from "../f08/shared";
import "../../styles/f11.css";

export function DissolveSummary({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <div className="row">
        <b>{text(p.goal)}</b>
        <Badge tone="measured">{text(p.outcome)}</Badge>
      </div>
      <Fields values={obj(p.counts)} />
      <Table data={p.contributions} columns={["participant", "tasks", "hours"]} />
      <span className="small">{text(p.cost)}</span>
      <div className="row">
        <Action
          label="Download sealed log"
          event="log.download"
          send={send}
          data={{ log: p.log }}
        />
        <Action label="Open results" event="results.open" send={send} />
      </div>
    </>
  );
}
