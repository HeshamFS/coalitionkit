// SPDX-License-Identifier: Apache-2.0
import { type KeyboardEvent, useEffect, useId, useRef, useState } from "react";
import { Glyph } from "./Glyph";
import { type Props, rows, str } from "./shared";

const keyOf = (item: Props) => str(item.id, str(item.value));
type ChoiceProps = { p: Props; value: unknown; pick: (value: string) => void };
export function ChoiceMenu({ p, value, pick }: ChoiceProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(() =>
    Math.max(
      0,
      rows(p.options).findIndex((item) => value === keyOf(item)),
    ),
  );
  const ref = useRef<HTMLDivElement>(null);
  const id = useId();
  const options = rows(p.options).filter((item) =>
    str(item.label).toLocaleLowerCase().includes(query.toLocaleLowerCase()),
  );
  const selected = rows(p.options).filter((item) =>
    Array.isArray(value) ? value.includes(keyOf(item)) : value === keyOf(item),
  );
  useEffect(() => {
    const outside = (event: PointerEvent) => {
      if (!ref.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, []);
  const choose = (key: string) => {
    pick(key);
    setQuery("");
    if (!p.multiple) setOpen(false);
  };
  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      setActive((index) =>
        Math.max(0, Math.min(options.length - 1, index + (event.key === "ArrowDown" ? 1 : -1))),
      );
    }
    if (event.key === "Enter" && open && options[active]) {
      event.preventDefault();
      const item = options[active];
      if (!item.disabled) choose(keyOf(item));
    }
  };
  const trigger = {
    className: "f01-choice-trigger",
    role: "combobox" as const,
    "aria-label": "Choose an option",
    "aria-expanded": open,
    "aria-controls": id,
    "aria-haspopup": "listbox" as const,
    "aria-activedescendant": open && options[active] ? `${id}-${active}` : undefined,
    onKeyDown,
  };
  return (
    <div className="f01-choice" ref={ref}>
      <div className={`f01-choice-control ${open ? "is-open" : ""}`}>
        {!!p.multiple &&
          selected.map((item) => (
            <button
              className="chip chip-on"
              type="button"
              key={keyOf(item)}
              onClick={() => pick(keyOf(item))}
              aria-label={`Remove ${str(item.label)}`}
            >
              {str(item.label)} ×
            </button>
          ))}
        {p.multiple ? (
          <input
            {...trigger}
            value={query}
            placeholder="add…"
            onClick={() => setOpen(true)}
            onChange={(event) => {
              setQuery(event.target.value);
              setActive(0);
              setOpen(true);
            }}
          />
        ) : (
          <button {...trigger} type="button" onClick={() => setOpen(!open)}>
            <span>{str(selected[0]?.label, "Choose…")}</span>
            <Glyph name="down" size="sm" />
          </button>
        )}
      </div>
      {open && (
        <ChoiceOptions
          id={id}
          options={options}
          multiple={!!p.multiple}
          value={value}
          active={active}
          choose={choose}
        />
      )}
    </div>
  );
}
function ChoiceOptions({
  id,
  options,
  multiple,
  value,
  active,
  choose,
}: {
  id: string;
  options: Props[];
  multiple: boolean;
  value: unknown;
  active: number;
  choose: (id: string) => void;
}) {
  return (
    <div
      className="f01-menu"
      id={id}
      role="listbox"
      aria-label="Options"
      aria-multiselectable={multiple || undefined}
    >
      {options.map((item, index) => {
        const selected = Array.isArray(value) ? value.includes(keyOf(item)) : value === keyOf(item);
        return (
          <button
            id={`${id}-${index}`}
            className={index === active ? "is-active" : ""}
            type="button"
            role="option"
            aria-selected={selected}
            disabled={!!item.disabled}
            key={keyOf(item)}
            onClick={() => choose(keyOf(item))}
          >
            {multiple && (
              <span className={`box ${selected ? "box-on" : ""}`}>
                {selected && <Glyph name="check" size="sm" />}
              </span>
            )}
            <span>{str(item.label)}</span>
            {item.hint ? <small>{str(item.hint)}</small> : null}
            {!multiple && selected && (
              <span className="h-right blue">
                <Glyph name="check" size="sm" />
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
