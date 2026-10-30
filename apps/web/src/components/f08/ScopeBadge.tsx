// SPDX-License-Identifier: Apache-2.0
import { list, type Props, type Send, text } from "./shared";

export function ScopeBadge({ p }: { p: Props; send: Send }) {
  const audience = text(p.audience);
  const redacted = list(p.redact).length > 0;
  const description = redacted
    ? "with a redaction"
    : audience === "host"
      ? "only the host (and steward)"
      : audience === "self"
        ? "you and the host"
        : audience.startsWith("task:")
          ? `people on task ${audience.slice(5)}`
          : audience.startsWith("role:")
            ? "everyone holding a role"
            : audience === "public"
              ? "outside the coalition; asks first"
              : "every member";
  return (
    <div className="row">
      <span className={`scope ${audience === "public" ? "f08-public" : ""}`}>
        {audience}
        {redacted && ` − ${text(p.redact)}`}
      </span>
      <span className="small">{description}</span>
    </div>
  );
}
