// SPDX-License-Identifier: Apache-2.0
import { Action, type Props, type Send, text, usePreviewState } from "../f08/shared";
import "../../styles/f10.css";

export function DeviceAlarm({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  if (preview === "cleared")
    return <span className="badge b-measured">Cleared · reading within bounds</span>;
  return (
    <div className="f10-alarm" role="alert">
      <b>{text(p.device)} out of range</b>
      <p>
        {text(p.reading)}, threshold {text(p.threshold)} for {text(p.duration)} s.
      </p>
      <p className="small">{text(p.autoAction)}</p>
      <div className="row">
        <Action label="Stop the run" event="alarm.stop" send={send} data={{ device: p.device }} />
        <Action label="Acknowledge" event="alarm.ack" send={send} data={{ device: p.device }} />
      </div>
    </div>
  );
}
