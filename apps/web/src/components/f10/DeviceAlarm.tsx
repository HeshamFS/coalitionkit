// SPDX-License-Identifier: Apache-2.0
import { Action, num, type Props, type Send, text, usePreviewState } from "../f08/shared";
import "../../styles/f10.css";
export function DeviceAlarm({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  if (preview === "cleared")
    return <span className="badge b-measured">Cleared · reading within bounds</span>;
  return (
    <div className="f10-alarm" role="alert">
      <div className="row">
        <svg className="ico family-bad" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 3l10 18H2zM12 10v4M12 17h.01" />
        </svg>
        <b>{text(p.device)} over setpoint</b>
      </div>
      <span className="small">
        {num(p.reading).toLocaleString("fr-FR")} units, {num(p.reading) - num(p.threshold)} above
        setpoint for{" "}
        {num(p.duration) >= 60 ? `${num(p.duration) / 60} min` : `${num(p.duration)} s`}.{" "}
        {text(p.autoAction)}
      </span>
      <div className="row">
        <Action label="Stop the run" event="alarm.stop" send={send} data={{ device: p.device }} />
        <Action label="Acknowledge" event="alarm.ack" send={send} data={{ device: p.device }} />
      </div>
    </div>
  );
}
