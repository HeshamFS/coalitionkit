// SPDX-License-Identifier: Apache-2.0
import { useEffect, useId, useRef, useState } from "react";
import { Glyph as Icon } from "./Glyph";
import { Children, number, rows, str, type ViewProps } from "./shared";

export function Overlay({ name, p, send, build }: ViewProps) {
  const ref = useRef<HTMLDivElement>(null);
  const title = useId();
  const modal = name === "Modal" || name === "Sheet";
  const [dismissed, setDismissed] = useState(false);
  const visible = !dismissed && (!modal || !!p.open);
  const dismissible = !modal || !!p.dismissible;
  const close = () => {
    if (!dismissible) return;
    setDismissed(true);
    send(modal ? "dismiss" : name === "Drawer" ? "drawer.close" : "popover.close");
  };
  useEffect(() => {
    if (!visible || !modal) return;
    const previous = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    return () => previous?.focus();
  }, [visible, modal]);
  useOverlayAnchor({
    ref,
    anchorId: str(p.anchor),
    title,
    visible,
    dismissible,
    name,
    modal,
    send,
    setDismissed,
  });

  if (!visible) return null;
  return (
    <div className={`f01-overlay f01-${name}`}>
      <div
        ref={ref}
        id={`${title}-dialog`}
        role="dialog"
        aria-modal={modal || undefined}
        aria-labelledby={p.title ? title : undefined}
        aria-label={p.title ? undefined : "Details"}
        tabIndex={-1}
        className="f01-dialog"
        style={
          name === "Drawer"
            ? {
                width: Math.min(480, Math.max(360, number(p.width, 380))),
                marginLeft: p.side === "left" ? 0 : "auto",
              }
            : undefined
        }
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.stopPropagation();
            close();
          }
          if (e.key === "Tab" && modal) {
            const nodes = ref.current?.querySelectorAll<HTMLElement>(
              'button:not(:disabled), input, select, textarea, a[href], [tabindex="0"]',
            );
            if (!nodes?.length) {
              e.preventDefault();
              return;
            }
            const first = nodes[0];
            const last = nodes[nodes.length - 1];
            if (
              e.shiftKey &&
              (document.activeElement === first || document.activeElement === ref.current)
            ) {
              e.preventDefault();
              last?.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
              e.preventDefault();
              first?.focus();
            }
          }
        }}
      >
        {name === "Sheet" && <span className="f01-handle" />}
        <div className="head" hidden={!p.title && name !== "Drawer"}>
          <h3 id={title}>{str(p.title)}</h3>
          {dismissible && name === "Drawer" && (
            <button
              type="button"
              className="icon-btn h-right"
              aria-label={`Close ${str(p.title)}`}
              onClick={close}
            >
              ×
            </button>
          )}
        </div>
        <Children value={p.body ?? p.children} build={build} />
        <footer>
          <Children value={p.footer} build={build} />
        </footer>
      </div>
    </div>
  );
}

function useOverlayAnchor({
  ref,
  anchorId,
  title,
  visible,
  dismissible,
  name,
  modal,
  send,
  setDismissed,
}: {
  ref: React.RefObject<HTMLDivElement | null>;
  anchorId: string;
  title: string;
  visible: boolean;
  dismissible: boolean;
  name: string;
  modal: boolean;
  send: ViewProps["send"];
  setDismissed: (value: boolean) => void;
}) {
  useEffect(() => {
    const anchor = document.getElementById(anchorId);
    const previous = anchor?.getAttribute("aria-details");
    if (visible) anchor?.setAttribute("aria-details", `${title}-dialog`);
    const outside = (event: PointerEvent) => {
      if (!visible || !dismissible || name === "Drawer") return;
      if (ref.current?.contains(event.target as Node) || anchor?.contains(event.target as Node))
        return;
      setDismissed(true);
      send(modal ? "dismiss" : "popover.close");
    };
    document.addEventListener("pointerdown", outside);
    return () => {
      document.removeEventListener("pointerdown", outside);
      if (previous) anchor?.setAttribute("aria-details", previous);
      else anchor?.removeAttribute("aria-details");
    };
  }, [anchorId, visible, dismissible, name, modal, send, title, ref, setDismissed]);
}

export function Menu({ p, send }: ViewProps) {
  return (
    <div className="f01-menu">
      {rows(p.items).map((item) => (
        <div key={str(item.id, str(item.label))}>
          {Array.isArray(item.submenu) ? (
            <details>
              <summary>
                {item.icon ? <Icon name={str(item.icon)} size="sm" /> : null}
                {str(item.label)}
                <span className="h-right">
                  <Icon name="right" size="sm" />
                </span>
              </summary>
              <Menu name="Menu" p={{ items: item.submenu }} send={send} build={() => null} />
            </details>
          ) : (
            <button
              type="button"
              disabled={!!item.disabled}
              className={item.tone === "danger" ? "f01-error" : ""}
              onClick={() => send("menu.pick", { id: item.id ?? item.label })}
            >
              {item.icon ? <Icon name={str(item.icon)} size="sm" /> : null}
              <span>{str(item.label)}</span>
              {item.shortcut ? <kbd>{str(item.shortcut)}</kbd> : null}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

export function Split({ p, send }: ViewProps) {
  const [open, setOpen] = useState(false);
  const items = rows(p.items);
  const primary = items.find((i) => i.value === p.primary) ?? items[0];
  return (
    <div className="f01-split">
      <div className="f01-button-group">
        <button
          type="button"
          className="btn btn-primary"
          disabled={!!primary?.disabled}
          onClick={() => send("action.invoke", { value: primary?.value })}
        >
          {str(primary?.label, "Choose")}
        </button>
        <button
          type="button"
          className="btn btn-primary f01-split-toggle"
          aria-label="More actions"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          <svg className="ico" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>
      </div>
      {open && (
        <div className="f01-menu">
          {items.map((i) => (
            <button
              type="button"
              key={str(i.value)}
              disabled={!!i.disabled}
              onClick={() => {
                send("action.invoke", { value: i.value });
                setOpen(false);
              }}
            >
              <span className="f01-menu-check">
                {i === primary && <Icon name="check" size="sm" />}
              </span>
              <span>{str(i.label)}</span>
              {i.hint ? <small>{str(i.hint)}</small> : null}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function Tooltip({ p }: ViewProps) {
  const id = useId();
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const root = document.getElementById(str(p.target));
    const target = root?.querySelector<HTMLElement>("button, input, a, [tabindex]") ?? root;
    if (!target) return;
    let timer: ReturnType<typeof setTimeout>;
    const show = () => setOpen(true);
    const hover = () => {
      timer = setTimeout(show, 400);
    };
    const hide = () => {
      clearTimeout(timer);
      setOpen(false);
    };
    const old = target.getAttribute("aria-describedby");
    const tabIndex = target.getAttribute("tabindex");
    if (target === root && tabIndex === null) target.tabIndex = 0;
    target.setAttribute("aria-describedby", id);
    target.addEventListener("mouseenter", hover);
    target.addEventListener("mouseleave", hide);
    target.addEventListener("focus", show);
    target.addEventListener("blur", hide);
    return () => {
      hide();
      if (old) target.setAttribute("aria-describedby", old);
      else target.removeAttribute("aria-describedby");
      if (target === root && tabIndex === null) target.removeAttribute("tabindex");
      target.removeEventListener("mouseenter", hover);
      target.removeEventListener("mouseleave", hide);
      target.removeEventListener("focus", show);
      target.removeEventListener("blur", hide);
    };
  }, [id, p.target]);
  return (
    <span id={id} role="tooltip" className="f01-tooltip" hidden={!open}>
      {str(p.tip)}
    </span>
  );
}
