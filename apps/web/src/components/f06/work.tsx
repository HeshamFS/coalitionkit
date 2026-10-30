// SPDX-License-Identifier: Apache-2.0
import { Avatar, Badge, cx, type Seat, Tag } from "../primitives";

/** A number is only ever shown from a bound value: the display form plus the event it came from. */
export type BoundNumber = { value: number; event_ref?: string };
export type Participant = { seat: Seat; label: string };

export function Bound({ n, unit }: { n: BoundNumber; unit?: string }) {
  return (
    <span className="num" title={n.event_ref ? `from event ${n.event_ref}` : undefined}>
      {n.value}
      {unit ? ` ${unit}` : ""}
    </span>
  );
}

/* ---------- TaskCard ---------- */

export type TaskStatus =
  | "open"
  | "negotiating"
  | "proposed"
  | "decided"
  | "committed"
  | "done"
  | "withdrawn";

const TRACK: { key: Exclude<TaskStatus, "withdrawn">; label: string }[] = [
  { key: "open", label: "open" },
  { key: "negotiating", label: "negot." },
  { key: "proposed", label: "proposed" },
  { key: "decided", label: "decided" },
  { key: "committed", label: "committed" },
  { key: "done", label: "done" },
];

function StatusMark({ status }: { status: TaskStatus }) {
  switch (status) {
    case "decided":
      return <Tag kind="agreed" />;
    case "committed":
      return <Tag kind="agreed" label="Committed" />;
    case "done":
      return <Badge kind="measured" label="done" />;
    case "proposed":
      return <Badge kind="signed" label="proposed" />;
    case "negotiating":
      return <Badge kind="model" label="negotiating" />;
    default:
      return <Badge kind="estimate" label={status} />;
  }
}

export function TaskCard({
  taskId,
  title,
  assignee,
  window: when,
  status,
  waitsFor = [],
  unblocks = [],
  evidence,
  onOpen,
  onDone,
}: {
  taskId: string;
  title: string;
  assignee?: Participant;
  window?: string;
  status: TaskStatus;
  waitsFor?: string[];
  unblocks?: string[];
  evidence?: string;
  onOpen?: () => void;
  onDone?: () => void;
}) {
  const index = TRACK.findIndex((t) => t.key === status);
  const withdrawn = status === "withdrawn";
  const deps = [
    waitsFor.length ? `waits for ${waitsFor.join(", ")}` : "",
    unblocks.length ? `unblocks ${unblocks.join(", ")}` : "",
  ]
    .filter(Boolean)
    .join(" · ");
  const compactCard = status === "done" || withdrawn;
  return (
    <article
      className="card f06-task"
      aria-label={`Task ${title}, ${status}`}
      style={{
        opacity: withdrawn ? "var(--f06-inactive-opacity, .6)" : 1,
        boxShadow: compactCard ? undefined : "var(--shadow)",
      }}
    >
      <div className="head">
        <span className="mono st">{taskId}</span>
        <span className="h-title">
          {onOpen && !withdrawn ? (
            <button type="button" className="f06-task-open" aria-label="Open" onClick={onOpen}>
              {title}
            </button>
          ) : (
            title
          )}
        </span>
        <span className="h-right">
          <StatusMark status={status} />
        </span>
      </div>
      {assignee && !compactCard && (
        <div className="row">
          <Avatar seat={assignee.seat} label={assignee.label} size="xs" />
          <span className="small">
            {assignee.label}
            {when ? ` · ${when}` : ""}
          </span>
        </div>
      )}
      {!compactCard && (
        <>
          <div className="row" style={{ gap: 3 }} aria-hidden="true">
            {TRACK.map((t, i) => (
              <span key={t.key} className="bar grow" style={{ height: 4 }}>
                {i <= index && (
                  <span
                    style={{
                      width: "100%",
                      background: i === index ? "var(--blue)" : "var(--ink-3)",
                    }}
                  />
                )}
              </span>
            ))}
          </div>
          <div className="row sp st" aria-hidden="true">
            {TRACK.map((t, i) => (
              <span
                key={t.key}
                className={i === index ? "blue" : undefined}
                style={i === index ? { fontWeight: 600 } : undefined}
              >
                {t.label}
              </span>
            ))}
          </div>
        </>
      )}
      {deps && !compactCard && (
        <div className="row small">
          <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M9 6l6 6-6 6" />
          </svg>
          {deps}
        </div>
      )}
      {status === "done" && (assignee || evidence) && (
        <span className="small">
          {assignee?.label}
          {evidence ? ` · evidence: ${evidence}` : ""}
        </span>
      )}
      {onDone && status === "committed" && (
        <button type="button" className="btn btn-sm btn-primary" onClick={onDone}>
          Mark done
        </button>
      )}
    </article>
  );
}

/* ---------- NeedCard ---------- */

export type NeedState = "open" | "matched" | "fulfilled" | "withdrawn";

export function NeedCard({
  needId,
  owner,
  text,
  state,
  offers = 0,
  meta,
  onOpen,
  onWithdraw,
}: {
  needId: string;
  owner: Participant;
  text: string;
  state: NeedState;
  offers?: number;
  meta?: string;
  onOpen?: () => void;
  onWithdraw?: () => void;
}) {
  const withdrawn = state === "withdrawn";
  return (
    <article
      className={cx("card", "f06-need", state === "matched" && "card-live")}
      tabIndex={onOpen ? 0 : undefined}
      role={onOpen ? "button" : undefined}
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen?.();
        }
        if (event.key === "Delete" && state === "open") {
          event.preventDefault();
          onWithdraw?.();
        }
      }}
      data-need={needId}
      data-state={state}
      aria-keyshortcuts={state === "open" ? "Enter Space Delete" : "Enter Space"}
      aria-label={`Need ${text}, ${state}`}
      style={{ opacity: withdrawn ? "var(--f06-inactive-opacity, .55)" : 1 }}
    >
      <div className="head">
        <Avatar seat={owner.seat} label={owner.label} />
        <span
          className="h-title"
          style={withdrawn ? { textDecoration: "line-through" } : undefined}
        >
          {text}
        </span>
        {state === "fulfilled" && (
          <span className="h-right">
            <Tag kind="agreed" />
          </span>
        )}
      </div>
      <div className={withdrawn ? "col" : "row"}>
        <Badge
          kind={state === "matched" ? "signed" : state === "fulfilled" ? "measured" : "estimate"}
          label={state}
        />
        {!withdrawn && (
          <span className="small">
            {state === "fulfilled"
              ? meta
              : `${offers} ${offers === 1 ? "offer" : "offers"}${meta ? ` · ${meta}` : ""}`}
          </span>
        )}
      </div>
    </article>
  );
}

/* ---------- OfferCard ---------- */

export type OfferState = "open" | "accepted" | "expired" | "withdrawn";

function shortTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? value
    : date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" });
}

/** A currency symbol goes before the amount ("€38"); any other unit after it ("12 min"). */
export function costText(value: number, unit?: string): string {
  if (!unit) return String(value);
  return /^\p{Sc}+$/u.test(unit) ? `${unit}${value}` : `${value} ${unit}`;
}

export function OfferCard({
  offerId,
  what,
  from,
  target,
  cost,
  expires,
  state,
  needsYou,
  scope,
  onAccept,
  onAsk,
  onWithdraw,
}: {
  offerId: string;
  what: string;
  from?: string;
  target?: string;
  cost?: { amount: BoundNumber; unit?: string; kind?: string };
  expires?: string;
  state: OfferState;
  needsYou?: boolean;
  scope?: string;
  onAccept?: () => void;
  onAsk?: () => void;
  onWithdraw?: () => void;
}) {
  const dead = state === "expired" || state === "withdrawn";
  const asking = state === "open" && needsYou;
  const meta = [from, target ? `for ${target}` : ""].filter(Boolean).join(" · ");
  return (
    <article
      className={cx("card", asking && "card-ask")}
      data-offer={offerId}
      tabIndex={state === "open" && onWithdraw ? 0 : undefined}
      aria-keyshortcuts={state === "open" ? "Delete" : undefined}
      onKeyDown={(event) => {
        if (event.key === "Delete" && state === "open" && event.target === event.currentTarget) {
          event.preventDefault();
          onWithdraw?.();
        }
      }}
      aria-label={`Offer ${what}, ${state}`}
      style={{ opacity: dead ? "var(--f06-inactive-opacity, .55)" : 1 }}
    >
      <div className="head">
        <span
          className="h-title"
          style={state === "withdrawn" ? { textDecoration: "line-through" } : undefined}
        >
          {what}
        </span>
        <span className="h-right">
          {asking && <Tag kind="needs" />}
          {state === "accepted" && <Tag kind="agreed" />}
          {state === "open" && !asking && scope === "private" && <Tag kind="private" />}
          {state === "open" && !asking && scope !== "private" && (
            <Badge kind="estimate" label="quote" />
          )}
          {state === "withdrawn" && <Badge kind="estimate" label={state} />}
        </span>
      </div>
      {meta && !dead && <span className="small">{meta}</span>}
      {scope === "private" && !meta && (
        <span className="small">only the people named here and the host see it</span>
      )}
      {cost && !dead && (
        <div className="row">
          <span className="num small" title={`from event ${cost.amount.event_ref}`}>
            {costText(cost.amount.value, cost.unit)}
          </span>
          {expires && !dead && (
            <span className="h-right small">
              expires <time dateTime={expires}>{shortTime(expires)}</time>
            </span>
          )}
        </div>
      )}
      {state === "expired" && expires && (
        <span className="small">
          expired <time dateTime={expires}>{shortTime(expires)}</time>
        </span>
      )}
      {asking && (
        <div className="row">
          <button type="button" className="btn btn-sm btn-primary" onClick={onAccept}>
            Accept
          </button>
          <button type="button" className="btn btn-sm" onClick={onAsk}>
            Ask
          </button>
        </div>
      )}
    </article>
  );
}

/* ---------- Timeline ---------- */

export type TimelineItem = {
  when: string;
  title: string;
  assignee?: string;
  state: "done" | "now" | "next";
};

export function Timeline({ items }: { items: TimelineItem[] }) {
  return (
    <ol
      className="col f06-timeline"
      aria-label="Timeline"
      style={{
        gap: 0,
        borderLeft: "2px solid var(--line)",
        marginLeft: 6,
        paddingLeft: 12,
        listStyle: "none",
        margin: "0 0 0 6px",
      }}
    >
      {items.map((it, i) => {
        const now = it.state === "now";
        const last = i === items.length - 1;
        return (
          <li
            key={`${it.when}-${it.title}`}
            aria-current={now ? "step" : undefined}
            style={{ position: "relative", padding: last ? "4px 0 0" : "4px 0 10px" }}
          >
            <span
              className={cx("pin", now && "pulse")}
              style={{
                position: "absolute",
                left: -18,
                top: 8,
                background:
                  it.state === "done" ? "var(--ok-fg)" : now ? "var(--blue)" : "var(--line-strong)",
              }}
            />
            <span className={cx("st", now && "blue")}>
              {it.when}
              {now ? " · now" : ""}
              <span className="sr-only">{`, ${it.state === "done" ? "done" : it.state === "now" ? "happening now" : "upcoming"}`}</span>
            </span>
            <div className="small" style={{ color: "var(--ink)" }}>
              {now ? <b>{it.title}</b> : it.title}
              {it.assignee ? ` · ${it.assignee}` : ""}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
