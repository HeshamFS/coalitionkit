// SPDX-License-Identifier: Apache-2.0
import { useContext } from "react";
import { PrivacyCharterRevision } from "./presentation";
import { Action, type Props, type Send, text } from "./shared";
export function CommitmentCard({ p, send }: { p: Props; send: Send }) {
  const status = text(p.status);
  const charterRevision = useContext(PrivacyCharterRevision);
  const tag =
    status === "pending"
      ? ["needs", "Needs you"]
      : status === "approved"
        ? ["agreed", "Agreed"]
        : ["blocked", "Blocked"];
  return (
    <>
      <div className="head">
        <span className="h-title">{text(p.task)}</span>
        {status !== "withdrawn" && <span className={`h-right tag t-${tag[0]}`}>{tag[1]}</span>}
      </div>
      <span className="small">
        {status === "pending"
          ? "pending · your owner must approve"
          : status === "approved"
            ? `approved · ${text(p.assignee)} · due ${text(p.due)}`
            : status === "suspended"
              ? `suspended until you accept ${charterRevision ? `charter r${charterRevision}` : "the current charter"}`
              : `${status} · task back to negotiating`}
      </span>
      {status === "pending" && (
        <div className="row">
          <Action
            label="Approve"
            event="commit.approve"
            send={send}
            data={{ subject: p.subject, commitment_id: p.commitment_id }}
            disabled={Date.parse(text(p.decision_deadline)) <= Date.now()}
            primary
          />
          <Action
            label="Withdraw"
            event="commit.withdraw"
            send={send}
            data={{ subject: p.subject, commitment_id: p.commitment_id }}
          />
        </div>
      )}
    </>
  );
}
