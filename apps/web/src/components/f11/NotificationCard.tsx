// SPDX-License-Identifier: Apache-2.0
import { type Props, type Send, text } from "../f08/shared";
import "../../styles/f11.css";
export function NotificationCard({ p, send }: { p: Props; send: Send }) {
  return (
    <button
      type="button"
      className="f11-notification"
      onClick={() => send("notification.open", { link: p.link })}
    >
      <span className="av av-sq">C</span>
      <span className="col grow">
        <span className="row">
          <b>{text(p.title)}</b>
          <span className="h-right st">{text(p.ageLabel ?? "now")}</span>
        </span>
        <span>{text(p.body)}</span>
      </span>
    </button>
  );
}
