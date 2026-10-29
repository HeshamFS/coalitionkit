// SPDX-License-Identifier: Apache-2.0
import { type ReactNode, useEffect, useState } from "react";
import { Icon, type IconName } from "../ui/Icon";
import { cx } from "./primitives";

/* ---------- Banner ---------- */

export type BannerTone = "info" | "ask" | "blocked" | "agreed";
const BANNER_CLASS: Record<BannerTone, string> = {
  info: "bn-info",
  ask: "bn-warn",
  blocked: "bn-bad",
  agreed: "bn-ok",
};
const BANNER_ICON: Record<BannerTone, IconName> = {
  info: "info",
  ask: "info",
  blocked: "shield",
  agreed: "check",
};

export function Banner({
  tone,
  title,
  body,
  action,
  onAction,
  onDismiss,
}: {
  tone: BannerTone;
  title: string;
  body?: string;
  action?: string;
  onAction?: () => void;
  onDismiss?: () => void;
}) {
  return (
    <div
      className={cx("banner", BANNER_CLASS[tone])}
      role={tone === "blocked" ? "alert" : "status"}
    >
      <Icon name={BANNER_ICON[tone]} />
      <div className="grow">
        <b>{title}</b>
        {body ? ` ${body}` : ""}
      </div>
      {action && (
        <button type="button" className="btn btn-sm" onClick={onAction}>
          {action}
        </button>
      )}
      {onDismiss && (
        <button type="button" className="icon-btn" aria-label="Dismiss" onClick={onDismiss}>
          <Icon name="x" size="sm" />
        </button>
      )}
    </div>
  );
}

/* ---------- Toast ---------- */

/** Bounds for numbers a composed tree controls. */
export const clamp = (n: number, lo: number, hi: number) =>
  Math.min(hi, Math.max(lo, Math.round(n)));

export type ToastTone = "done" | "change" | "error";

export function Toast({
  tone,
  text,
  action,
  undoWindow: undoRaw,
  onAction,
  onUndo,
  onDismiss,
}: {
  tone: ToastTone;
  text: string;
  action?: string;
  /** Seconds the undo stays available. The toast dismisses itself when it runs out. */
  undoWindow?: number;
  onAction?: () => void;
  onUndo?: () => void;
  onDismiss?: () => void;
}) {
  const undoWindow = undoRaw ? clamp(undoRaw, 1, 60) : 0;
  const [left, setLeft] = useState(undoWindow);
  useEffect(() => {
    if (!undoWindow) return;
    setLeft(undoWindow);
    const timer = setInterval(() => {
      setLeft((n) => {
        if (n <= 1) {
          clearInterval(timer);
          onDismiss?.();
          return 0;
        }
        return n - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [undoWindow, onDismiss]);

  const light = tone === "error";
  const label = text.length > 60 ? `${text.slice(0, 59)}…` : text;
  return (
    <div className={cx("toast", light && "toast-light")} role={light ? "alert" : "status"}>
      {tone === "done" && <Icon name="check" />}
      {tone === "change" && (
        <span
          className="live-dot pulse"
          style={{ background: "var(--dark-blue)" }}
          aria-hidden="true"
        />
      )}
      {tone === "error" && <Icon name="info" />}
      <span>{label}</span>
      {undoWindow ? (
        <button
          type="button"
          className="act"
          style={{ background: "none", border: 0, cursor: "pointer", font: "inherit" }}
          onClick={onUndo}
        >
          Undo {"·"} {left} s
        </button>
      ) : (
        action && (
          <button
            type="button"
            className="act"
            style={{
              background: "none",
              border: 0,
              cursor: "pointer",
              font: "inherit",
              color: light ? "var(--blue-text)" : undefined,
            }}
            onClick={onAction}
          >
            {action}
          </button>
        )
      )}
      {onDismiss && (
        <button
          type="button"
          className="icon-btn"
          style={{ color: "inherit", width: 20, height: 20 }}
          aria-label="Dismiss"
          onClick={onDismiss}
        >
          <Icon name="x" size="sm" />
        </button>
      )}
    </div>
  );
}

/** Newest on top, three at most. */
export function ToastStack({ children }: { children: ReactNode[] }) {
  return (
    <div className="col" aria-live="polite">
      {children.slice(-3).reverse()}
    </div>
  );
}

/* ---------- EmptyState, ErrorState ---------- */

export function EmptyState({
  glyph = "inbox",
  title,
  body,
  action,
  onAction,
}: {
  glyph?: IconName;
  title: string;
  body: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <section className="empty card card-dashed" aria-label={title}>
      <div className="glyph">
        <Icon name={glyph} size="lg" />
      </div>
      <b style={{ fontSize: 14 }}>{title}</b>
      <span className="small">{body}</span>
      {action && (
        <button type="button" className="btn btn-sm" onClick={onAction}>
          {action}
        </button>
      )}
    </section>
  );
}

export function ErrorState({
  state = "error",
  cause,
  lastSeen,
  retry = true,
  details,
  missed = 0,
  onRetry,
}: {
  state?: "error" | "reconnecting";
  cause: string;
  lastSeen?: string;
  retry?: boolean;
  details?: { code: string; ref: string };
  missed?: number;
  onRetry?: () => void;
}) {
  const [open, setOpen] = useState(false);
  if (state === "reconnecting") {
    return (
      <div className="dock" role="status" style={{ alignSelf: "flex-start" }}>
        <span className="spinner" style={{ color: "var(--warn-fg)", width: 10, height: 10 }} />
        Reconnecting {"·"} <b>{missed} missed events</b> will replay
      </div>
    );
  }
  return (
    <section className="empty card" style={{ borderColor: "var(--bad-line)" }} role="alert">
      <div
        className="glyph"
        style={{
          background: "var(--bad-bg)",
          borderColor: "var(--bad-line)",
          color: "var(--bad-fg)",
        }}
      >
        <Icon name="info" size="lg" />
      </div>
      <b style={{ fontSize: 14 }}>{cause}</b>
      <span className="small">
        {lastSeen ? `It last answered at ${lastSeen}. ` : ""}Nothing is lost; the host keeps your
        place.
      </span>
      <div className="row">
        {retry && (
          <button type="button" className="btn btn-sm" onClick={onRetry}>
            <Icon name="retry" size="sm" />
            Try again
          </button>
        )}
        {details && (
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            Details
          </button>
        )}
      </div>
      {open && details && (
        <span className="st">
          {details.code} {"·"} {details.ref}
        </span>
      )}
    </section>
  );
}

/* ---------- Skeleton (lifecycle: skeleton, filled, live, rest, changed) ---------- */

export type SkeletonState = "skeleton" | "filled" | "live" | "rest" | "changed";

function Bone({ w, h, round }: { w: number | string; h: number; round?: boolean }) {
  return (
    <span
      className="skel"
      style={{ width: w, height: h, borderRadius: round ? "50%" : undefined, display: "block" }}
    />
  );
}

export function Skeleton({
  shape = "card",
  lines: linesRaw = 2,
  reserves: reservesRaw,
  state = "skeleton",
  value,
  previous,
  label = "Loading",
}: {
  shape?: "line" | "block" | "avatar" | "card";
  lines?: number;
  /** Pixel height kept so the layout does not jump when the real content arrives. */
  reserves?: number;
  state?: SkeletonState;
  value?: string;
  previous?: string;
  label?: string;
}) {
  const lines = clamp(linesRaw, 1, 20);
  const reserves = reservesRaw === undefined ? undefined : clamp(reservesRaw, 0, 2000);
  if (state !== "skeleton") {
    const body = (
      <span className={cx(state === "filled" && "in")} aria-live="polite">
        {state === "live" && (
          <span className="live-dot pulse" style={{ display: "inline-block", marginRight: 6 }} />
        )}
        {state === "changed" && previous !== undefined && (
          <span className="mut3" style={{ textDecoration: "line-through", marginRight: 6 }}>
            {previous}
          </span>
        )}
        <span className={cx(state === "changed" && "flash")}>{value}</span>
      </span>
    );
    return (
      <div className="small" data-state={state} style={{ minHeight: reserves }}>
        {body}
      </div>
    );
  }
  const bones = (() => {
    if (shape === "avatar") return <Bone w={22} h={22} round />;
    if (shape === "line") return <Bone w="90%" h={10} />;
    if (shape === "block") return <Bone w="100%" h={reserves ?? 64} />;
    return (
      <div className="card">
        <div className="row">
          <Bone w={22} h={22} round />
          <Bone w={120} h={12} />
          <span className="h-right">
            <Bone w={56} h={18} />
          </span>
        </div>
        {Array.from({ length: lines }, (_, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: static placeholder rows
          <Bone key={i} w={i === 0 ? "90%" : "70%"} h={10} />
        ))}
        <div className="row">
          <Bone w={80} h={28} />
          <Bone w={64} h={28} />
        </div>
      </div>
    );
  })();
  return (
    <div
      aria-busy="true"
      aria-label={label}
      role="status"
      data-state="skeleton"
      style={{ minHeight: reserves }}
    >
      {bones}
    </div>
  );
}
