// SPDX-License-Identifier: Apache-2.0
import { useEffect, useId, useRef, useState } from "react";
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
  if (!visible) return null;
  return (
    <div className={`f01-overlay f01-${name}`}>
      <div
        ref={ref}
        role="dialog"
        aria-modal={modal || undefined}
        aria-labelledby={title}
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
        <div className="head">
          <h3 id={title}>{str(p.title)}</h3>
          {dismissible && (
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

export function Menu({ p, send }: ViewProps) {
  return (
    <div className="f01-menu">
      {rows(p.items).map((item) => (
        <div key={str(item.id, str(item.label))}>
          {Array.isArray(item.submenu) ? (
            <details>
              <summary>{str(item.label)}</summary>
              <Menu name="Menu" p={{ items: item.submenu }} send={send} build={() => null} />
            </details>
          ) : (
            <button
              type="button"
              disabled={!!item.disabled}
              className={item.tone === "danger" ? "f01-error" : ""}
              onClick={() => send("menu.pick", { id: item.id ?? item.label })}
            >
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
      <div className="row">
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
          className="btn"
          aria-label="More actions"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          ⌄
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
              {str(i.label)}
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
    target.setAttribute("aria-describedby", id);
    target.addEventListener("mouseenter", hover);
    target.addEventListener("mouseleave", hide);
    target.addEventListener("focus", show);
    target.addEventListener("blur", hide);
    return () => {
      hide();
      if (old) target.setAttribute("aria-describedby", old);
      else target.removeAttribute("aria-describedby");
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
