// SPDX-License-Identifier: Apache-2.0
import { Action, Badge, type Props, type Send, text, usePreviewState } from "../f08/shared";
import "../../styles/f11.css";

export function ChannelHandoff({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  if (preview === "expired")
    return <span className="small">This handoff expired. Review the current request.</span>;
  return (
    <>
      <div className="row">
        <Badge>{text(p.from)}</Badge>
        <span>→</span>
        <Badge tone="signed">{text(p.to)}</Badge>
      </div>
      <b>Continue on {text(p.to)}</b>
      <p className="small">{text(p.reason)} · your place is saved</p>
      <Action
        label={`Open ${text(p.to)}`}
        event="handoff.open"
        send={send}
        data={{ subject: p.subject, from: p.from, to: p.to }}
        primary
      />
    </>
  );
}
