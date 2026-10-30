// SPDX-License-Identifier: Apache-2.0
import { ShellIcon } from "./shell";
import { Frame, label, list, obj, text, type View } from "./ui";
import "./tray.css";

function deadline(value: unknown) {
  const raw = text(value);
  if (!raw) return "no deadline";
  const date = new Date(raw);
  if (!Number.isFinite(date.getTime())) return raw;
  const minutes = Math.ceil((date.getTime() - Date.now()) / 60000);
  if (minutes <= 0) return "overdue";
  if (minutes < 60) return `${minutes} min`;
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

export function ConsentTray({ p, send }: View) {
  const requests = list(p.requests).sort((a, b) => {
    const time = (v: unknown) => Date.parse(text(v)) || Number.POSITIVE_INFINITY;
    return time(a.deadline) - time(b.deadline);
  });
  return (
    <Frame name="ConsentTray" state={requests.length ? "pending" : "empty"}>
      <div className="f02-tray-heading">
        <ShellIcon name="Charter" />
        <b>
          {requests.length ? `${requests.length} things wait for you` : "Nothing needs your answer"}
        </b>
        {requests.length > 0 && <span>nothing happens without your answer</span>}
      </div>
      {requests.map((request, i) => (
        <div className="f02-tray-request" key={text(obj(request.subject).id) || String(i)}>
          <span className="f02-request-kind">
            {request.kind === "charter"
              ? "Charter"
              : request.kind === "commitment"
                ? "Approve"
                : "Decide"}
          </span>
          <b>{label(request) || text(request.kind)}</b>
          <time
            title={text(request.deadline)}
            dateTime={
              Number.isFinite(Date.parse(text(request.deadline)))
                ? text(request.deadline)
                : undefined
            }
          >
            {deadline(request.deadline)}
          </time>
          <button
            type="button"
            className={`ck-action${i === 0 ? " ck-primary" : ""}`}
            aria-label={`${label(request)} · Review`}
            onClick={() => send("consent.open", { subject: request.subject })}
          >
            {request.kind === "charter" ? "Read" : "Open"}
          </button>
        </div>
      ))}
    </Frame>
  );
}
