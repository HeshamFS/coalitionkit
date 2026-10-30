// SPDX-License-Identifier: Apache-2.0
import { Avatar, ScopeBadge, type Seat, Tag, type TagKind } from "./primitives";
import { number, obj, shown, str } from "./shared";
import { shortTime } from "./time";
export function DataCell({ value, format }: { value: unknown; format?: string }) {
  const record = obj(value);
  if (format === "scope") return <ScopeBadge audience={shown(value)} />;
  if (format === "status") {
    const label = shown(value);
    const kind = label.toLowerCase().replace("needs you", "needs") as TagKind;
    return ["agreed", "needs", "changed", "private", "blocked"].includes(kind) ? (
      <Tag kind={kind} label={label} />
    ) : (
      label
    );
  }
  if (format === "avatar") {
    const raw = record.seat;
    const seat: Seat =
      raw === "host" || raw === "steward"
        ? raw
        : (Math.max(1, Math.min(5, number(raw, 1))) as Seat);
    return (
      <span className="row">
        <Avatar label={str(record.label)} seat={seat} size="xs" />
        {str(record.label)}
      </span>
    );
  }
  if (format === "datetime")
    return (
      <time dateTime={str(value)} title={str(value)}>
        {shortTime(str(value))}
      </time>
    );
  return shown(value);
}
