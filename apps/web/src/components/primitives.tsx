// SPDX-License-Identifier: Apache-2.0
import type { CSSProperties, MouseEventHandler, ReactNode } from "react";
import { Icon } from "../ui/Icon";

export type Seat = 1 | 2 | 3 | 4 | 5 | "host" | "steward";
export type Scope = string;

const cx = (...parts: (string | false | undefined | null)[]) => parts.filter(Boolean).join(" ");

export { cx };

/* ---------- Text, Heading ---------- */

export function Text({
  text,
  variant = "body",
  tone = "default",
}: {
  text: string;
  variant?: "body" | "caption";
  tone?: "default" | "muted" | "blue";
}) {
  const style: CSSProperties =
    variant === "caption" ? { fontSize: 12, lineHeight: 1.45 } : { fontSize: 13, lineHeight: 1.5 };
  const color =
    tone === "muted" ? "var(--ink-2)" : tone === "blue" ? "var(--blue-text)" : "var(--ink)";
  return (
    <span style={{ ...style, color }} data-variant={variant} data-tone={tone}>
      {text}
    </span>
  );
}

const HEADING_STYLE: Record<"h1" | "h2" | "h3", CSSProperties> = {
  h1: { fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em", lineHeight: 1.15 },
  h2: { fontSize: 16, fontWeight: 700, letterSpacing: "-0.01em", lineHeight: 1.25 },
  h3: { fontSize: 13.5, fontWeight: 600, lineHeight: 1.3 },
};

export function Heading({
  text,
  variant = "h2",
  tone = "default",
}: {
  text: string;
  variant?: "h1" | "h2" | "h3";
  tone?: "default" | "blue";
}) {
  const Tag = variant;
  return (
    <Tag
      style={{
        margin: 0,
        ...HEADING_STYLE[variant],
        color: tone === "blue" ? "var(--blue-text)" : "var(--ink)",
      }}
    >
      {text}
    </Tag>
  );
}

/* ---------- Layout ---------- */

type Gap = 4 | 8 | 12 | 16;

export function Row({
  children,
  gap = 8,
  align = "center",
}: {
  children?: ReactNode;
  gap?: Gap;
  align?: "start" | "center" | "end";
}) {
  const alignItems = align === "start" ? "flex-start" : align === "end" ? "flex-end" : "center";
  return (
    <div className="row wrap" style={{ gap, alignItems }}>
      {children}
    </div>
  );
}

export function Column({ children, gap = 8 }: { children?: ReactNode; gap?: Gap }) {
  return (
    <div className="col" style={{ gap }}>
      {children}
    </div>
  );
}

export function Grid({
  children,
  columns = 2,
  gap = 12,
  compact = false,
}: {
  children?: ReactNode;
  columns?: 1 | 2 | 3 | 4;
  gap?: Gap;
  compact?: boolean;
}) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${compact ? 1 : columns}, minmax(0, 1fr))`,
        gap,
        alignItems: "start",
      }}
    >
      {children}
    </div>
  );
}

/* ---------- Containers ---------- */

export function ScopeBadge({ audience, redact }: { audience: Scope; redact?: string[] }) {
  const isPublic = audience === "public";
  const text = redact?.length ? `${audience} − ${redact.join(", ")}` : audience;
  return (
    <span
      className="scope"
      title={`Audience: ${text}`}
      style={isPublic ? { background: "var(--warn-bg)", color: "var(--warn-fg)" } : undefined}
    >
      <span className="sr-only">Audience </span>
      {text}
    </span>
  );
}

export function Card({
  children,
  title,
  tone = "default",
  scope,
  onOpen,
}: {
  children?: ReactNode;
  title?: string;
  tone?: "default" | "live" | "ask" | "dashed";
  scope?: Scope;
  onOpen?: () => void;
}) {
  const cls = cx(
    "card",
    tone === "live" && "card-live",
    tone === "ask" && "card-ask",
    tone === "dashed" && "card-dashed",
  );
  return (
    <div className={cls} {...(title ? { role: "group", "aria-label": title } : {})}>
      {(title || scope) && (
        <div className="head">
          {title && <span className="h-title">{title}</span>}
          {scope && (
            <span className="h-right">
              <ScopeBadge audience={scope} />
            </span>
          )}
        </div>
      )}
      {children}
      {onOpen && (
        <div className="row">
          <button type="button" className="btn btn-sm" onClick={onOpen}>
            Open
          </button>
        </div>
      )}
    </div>
  );
}

export function Panel({
  children,
  title,
  count,
  scope,
}: {
  children?: ReactNode;
  title?: string;
  count?: number;
  scope?: Scope;
}) {
  return (
    <section className="panel" aria-label={title}>
      {(title || scope) && (
        <div className="head">
          {title && <b style={{ fontSize: 13 }}>{title}</b>}
          {count !== undefined && <span className="count">{count}</span>}
          {scope && (
            <span className="h-right">
              <ScopeBadge audience={scope} />
            </span>
          )}
        </div>
      )}
      {children}
    </section>
  );
}

/* ---------- Button ---------- */

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "ink"
  | "ghost"
  | "soft"
  | "danger"
  | "danger-fill";
export type ForcedState = "hover" | "press" | "focus";

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: "btn-primary",
  secondary: "",
  ink: "btn-ink",
  ghost: "btn-ghost",
  soft: "btn-soft",
  danger: "btn-danger",
  "danger-fill": "btn-danger-fill",
};

export function Button({
  label,
  variant = "secondary",
  size = "md",
  disabled,
  busy,
  onClick,
  forceState,
  fill,
  hint,
}: {
  label: string;
  variant?: ButtonVariant;
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  busy?: boolean;
  onClick?: MouseEventHandler<HTMLButtonElement>;
  /** Gallery only: draws a pseudo state the browser would only show on interaction. */
  forceState?: ForcedState;
  fill?: boolean;
  hint?: string;
}) {
  const cls = cx(
    "btn",
    VARIANT_CLASS[variant],
    size === "sm" && "btn-sm",
    size === "lg" && "btn-lg",
    forceState === "hover" && "btn-hover",
    forceState === "press" && "btn-press",
    forceState === "focus" && "focus",
    fill && "btn-fill",
  );
  return (
    <button
      type="button"
      className={cls}
      disabled={disabled}
      aria-busy={busy || undefined}
      aria-disabled={busy || undefined}
      title={hint}
      onClick={busy ? undefined : onClick}
    >
      {busy && <span className="spinner" aria-hidden="true" />}
      {label}
    </button>
  );
}

/* ---------- Tag, Badge ---------- */

export type TagKind = "agreed" | "needs" | "changed" | "private" | "blocked";
const TAG_CLASS: Record<TagKind, string> = {
  agreed: "t-agreed",
  needs: "t-needs",
  changed: "t-changed",
  private: "t-private",
  blocked: "t-blocked",
};
const TAG_WORD: Record<TagKind, string> = {
  agreed: "Agreed",
  needs: "Needs you",
  changed: "Changed",
  private: "Private",
  blocked: "Blocked",
};

export function Tag({ kind, label }: { kind: TagKind; label?: string }) {
  return <span className={cx("tag", TAG_CLASS[kind])}>{label ?? TAG_WORD[kind]}</span>;
}

export type BadgeKind = "measured" | "vault" | "signed" | "model" | "estimate" | "example";

export function Badge({ label, kind = "estimate" }: { label: string; kind?: BadgeKind }) {
  return (
    <span className={cx("badge", `b-${kind}`)} data-kind={kind}>
      {label}
    </span>
  );
}

/* ---------- Avatar, AvatarStack ---------- */

/** Last word's first character: "Member 1" shows 1. */
export const glyphOf = (label: string) =>
  (label.trim().split(/\s+/).pop() ?? "").charAt(0).toUpperCase();

const SEAT_CLASS = (seat: Seat) => (typeof seat === "number" ? `s${seat}` : "sh");
const SIZE_CLASS = { xs: "av-xs", sm: "", lg: "av-lg", xl: "av-xl" } as const;

export function Avatar({
  seat,
  label,
  presence,
  ring,
  size = "sm",
  speaking,
}: {
  seat: Seat;
  label: string;
  presence?: "live" | "away" | "off";
  ring?: boolean;
  size?: "xs" | "sm" | "lg" | "xl";
  speaking?: boolean;
}) {
  const cls = cx(
    "av",
    SIZE_CLASS[size],
    SEAT_CLASS(seat),
    typeof seat !== "number" && "av-sq",
    presence && "presence",
    presence === "away" && "presence-away",
    presence === "off" && "presence-off",
    (ring || speaking) && "av-ring",
  );
  const status = presence ? `, ${presence === "live" ? "here" : presence}` : "";
  return (
    <span
      className={cls}
      role="img"
      aria-label={`${label}${status}${speaking ? ", speaking" : ""}`}
      title={label}
    >
      {glyphOf(label)}
    </span>
  );
}

export function AvatarStack({
  people,
  max = 3,
  size = "sm",
}: {
  people: { seat: Seat; label: string }[];
  max?: number;
  size?: "xs" | "sm" | "lg";
}) {
  const shown = people.slice(0, Math.min(20, Math.max(1, Math.round(max))));
  const extra = people.length - shown.length;
  return (
    // biome-ignore lint/a11y/useSemanticElements: a stack of avatars is a labelled group, not a form
    <div className="stack" role="group" aria-label={`${people.length} participants`}>
      {shown.map((p) => (
        <Avatar key={p.label} seat={p.seat} label={p.label} size={size} />
      ))}
      {extra > 0 && (
        <span
          className={cx("av", SIZE_CLASS[size])}
          style={{ background: "var(--surface-3)", color: "var(--ink-2)" }}
          role="img"
          aria-label={`${extra} more`}
        >
          +{extra}
        </span>
      )}
    </div>
  );
}

export { Icon };
