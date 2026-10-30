// SPDX-License-Identifier: Apache-2.0
import { Frame, list, text, type View } from "../f02/ui";
import "./digest.css";

export function ChannelDigest({ p }: View) {
  const items = list(p.items);
  if (p.channel === "sms")
    return (
      <Frame name="ChannelDigest" state="sent" tone="f03-digest-sms">
        {items.map((item) => text(item.text)).join(" ")}
      </Frame>
    );
  return (
    <Frame name="ChannelDigest" state="sent" tone="f03-digest-email">
      <header>
        <span>From: CoalitionKit</span>
        <b>{text(p.period)}</b>
      </header>
      <div className="f03-digest-body">
        {items.map((item, index) => (
          <div className="f03-digest-item" key={text(item.ref) || String(index)}>
            <span
              className={`tag ${text(item.tone).toLowerCase() === "needs you" ? "t-needs" : text(item.tone).toLowerCase() === "agreed" ? "t-agreed" : "t-changed"}`}
            >
              {text(item.tone)}
            </span>
            {text(item.text)}
          </div>
        ))}
        <a className="ck-action ck-primary" href="/">
          Open the coalition
        </a>
        <span className="f03-digest-note">decisions are never taken by email reply</span>
      </div>
    </Frame>
  );
}
