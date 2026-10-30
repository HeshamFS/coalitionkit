// SPDX-License-Identifier: Apache-2.0
import { Action, Badge, type Props, type Send, text } from "./shared";
import "../../styles/f08.css";

export function CommitmentCard({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <div className="row">
        <b>{text(p.task)}</b>
        <Badge>{text(p.status)}</Badge>
      </div>
      <span className="small">
        {text(p.assignee)} · due {text(p.due)}
      </span>
      {p.status === "pending" && (
        <Action
          label="Approve"
          event="commit.approve"
          send={send}
          data={{ subject: p.subject, commitment_id: p.commitment_id }}
          disabled={Date.parse(text(p.decision_deadline)) <= Date.now()}
          primary
        />
      )}
      {p.status !== "withdrawn" && (
        <Action
          label="Withdraw"
          event="commit.withdraw"
          send={send}
          data={{ subject: p.subject, commitment_id: p.commitment_id }}
        />
      )}
    </>
  );
}
