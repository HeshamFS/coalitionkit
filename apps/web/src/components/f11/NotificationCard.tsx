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
      <span className="row">
        <span className="av av-sq sh">C</span>
        <span className="st">CoalitionKit · now</span>
      </span>
      <b>{text(p.title)}</b>
      <span>{text(p.body)}</span>
    </button>
  );
}
