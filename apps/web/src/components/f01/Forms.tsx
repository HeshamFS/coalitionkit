// SPDX-License-Identifier: Apache-2.0
import { useEffect, useId, useRef, useState } from "react";
import { ChoiceMenu } from "./ChoiceMenu";
import { Glyph } from "./Glyph";
import { Avatar } from "./primitives";
import { number, obj, rows, shown, str, type ViewProps } from "./shared";

export function Field({ name, p, send }: ViewProps) {
  const id = useId();
  const [value, setValue] = useState(shown(p.value));
  useEffect(() => setValue(shown(p.value)), [p.value]);
  const error = str(p.error);
  const change = (v: string) => {
    setValue(v);
    send("change", {
      value: name === "NumberField" || name === "Slider" ? Number(v) : v,
      ...(p.unit ? { unit: p.unit } : {}),
    });
  };
  const common = {
    id,
    value,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      change(e.target.value),
    "aria-invalid": !!error,
    "aria-describedby": error ? `${id}-error` : undefined,
    className: "f01-input",
    maxLength: number(p.maxLength) || undefined,
  };
  return (
    <div className="f01-field">
      <label htmlFor={id}>
        {str(
          p.label,
          name === "DateTimeInput" ? "Date and time" : name === "Slider" ? "Value" : name,
        )}
      </label>
      {name === "TextArea" ? (
        <textarea {...common} rows={3} />
      ) : (
        <div className={name === "NumberField" && !p.unit ? "f01-number" : "row"}>
          {name === "NumberField" && !p.unit && (
            <button
              type="button"
              aria-label={`Decrease ${str(p.label)}`}
              disabled={p.min !== undefined && Number(value) <= number(p.min)}
              onClick={() =>
                change(
                  String(Math.max(number(p.min, -Infinity), Number(value) - number(p.step, 1))),
                )
              }
            >
              −
            </button>
          )}
          <input
            {...common}
            placeholder={str(p.placeholder)}
            type={
              name === "NumberField"
                ? "number"
                : name === "Slider"
                  ? "range"
                  : name === "DateTimeInput"
                    ? str(p.mode) === "datetime"
                      ? "datetime-local"
                      : str(p.mode, "date")
                    : "text"
            }
            min={p.min === undefined ? undefined : number(p.min)}
            max={p.max ? number(p.max) : undefined}
            step={number(p.step, 1)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && name === "TextField") send("submit", { value });
            }}
          />
          {name === "NumberField" && !p.unit && (
            <button
              type="button"
              aria-label={`Increase ${str(p.label)}`}
              disabled={p.max !== undefined && Number(value) >= number(p.max)}
              onClick={() =>
                change(String(Math.min(number(p.max, Infinity), Number(value) + number(p.step, 1))))
              }
            >
              +
            </button>
          )}
          {p.unit ? <span className="small">{str(p.unit)}</span> : null}
        </div>
      )}
      {p.tz ? <span className="small">{str(p.tz)}</span> : null}
      {error && (
        <span id={`${id}-error`} className="f01-error" role="alert">
          {error}
        </span>
      )}
      {name === "TextArea" && number(p.maxLength) > 0 && (
        <span className="st">
          {value.length} / {number(p.maxLength)}
        </span>
      )}
    </div>
  );
}

export function Toggle({ name, p, send }: ViewProps) {
  const [value, setValue] = useState(p.value);
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => setValue(p.value), [p.value]);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = value === "mixed";
  }, [value]);
  return (
    <label className="f01-toggle">
      <input
        type="checkbox"
        ref={ref}
        role={name === "Switch" ? "switch" : undefined}
        checked={value === true}
        aria-checked={value === "mixed" ? "mixed" : value === true}
        onChange={(e) => {
          setValue(e.target.checked);
          send("change", { value: e.target.checked });
        }}
      />
      <span>{str(p.label)}</span>
    </label>
  );
}

export function Choices({ name, p, send, build }: ViewProps) {
  const [value, setValue] = useState<unknown>(p.value);
  useEffect(() => setValue(p.value), [p.value]);
  const id = useId();
  const options = rows(p.options);
  const pick = (next: string) => {
    const v = p.multiple
      ? Array.isArray(value) && value.includes(next)
        ? value.filter((x) => x !== next)
        : [...(Array.isArray(value) ? value : []), next]
      : next;
    setValue(v);
    send(name === "RadioGroup" ? "change" : "select", { value: v });
  };
  if (name === "ChoicePicker" && (p.display === "menu" || p.multiple))
    return <ChoiceMenu p={p} value={value} pick={pick} />;
  return (
    <div>
      <div className={`f01-options f01-${name}`} role={name === "Tabs" ? "tablist" : undefined}>
        {options.map((o) => {
          const key = str(o.id);
          const selected = Array.isArray(value) ? value.includes(key) : value === key;
          return name === "RadioGroup" ? (
            <label key={key} className="f01-toggle">
              <input
                type="radio"
                name={id}
                checked={selected}
                onChange={() => pick(key)}
                disabled={!!o.disabled}
              />
              {str(o.label)}
              {o.hint ? <span className="small">{str(o.hint)}</span> : null}
              {o.count !== undefined && <span className="count">{shown(o.count)}</span>}
            </label>
          ) : (
            <button
              key={key}
              type="button"
              role={name === "Tabs" ? "tab" : undefined}
              {...(name === "Tabs" ? { "aria-selected": selected } : {})}
              aria-pressed={name !== "Tabs" ? selected : undefined}
              disabled={!!o.disabled}
              onClick={() => pick(key)}
            >
              {str(o.label)}
              {o.count !== undefined && <span className="count">{shown(o.count)}</span>}
            </button>
          );
        })}
      </div>
      {name === "Tabs" &&
      Array.isArray(p.panels) &&
      typeof p.panels[options.findIndex((o) => o.id === value)] === "string"
        ? build(p.panels[options.findIndex((o) => o.id === value)] as string)
        : null}
    </div>
  );
}

export function Search({ name, p, send }: ViewProps) {
  const incoming = str(p.query, str(obj(p.query).text));
  const [query, setQuery] = useState(incoming);
  useEffect(() => setQuery(incoming), [incoming]);
  const [active, setActive] = useState(0);
  const [open, setOpen] = useState(true);
  const groups = rows(obj(p.query).groups ?? p.groups)
    .map((group) => ({
      label: str(group.label),
      items: rows(group.items).filter((i) =>
        str(i.label).toLowerCase().includes(query.toLowerCase()),
      ),
    }))
    .filter((group) => group.items.length);
  const items = groups.flatMap((g) => g.items);
  const pick = (id: string) =>
    send(name === "CommandPalette" ? "command.run" : "search.pick", { id });
  return (
    <div className={`f01-search ${name === "CommandPalette" ? "f01-command" : ""}`}>
      <div className="f01-search-input">
        <Glyph name="search" size={name === "CommandPalette" ? undefined : "sm"} />
        <input
          className="f01-input"
          aria-label={name === "CommandPalette" ? "Command" : "Search"}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            setActive(0);
            if (name !== "CommandPalette") send("search.change", { q: e.target.value });
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") setOpen(false);
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setActive((v) => Math.min(items.length - 1, v + 1));
            }
            if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((v) => Math.max(0, v - 1));
            }
            if (e.key === "Enter") {
              if (items[active]) pick(str(items[active].id));
              else if (name === "CommandPalette") send("command.ask", { text: query });
            }
          }}
        />
        <kbd className="kbd">{name === "CommandPalette" ? "⌘K" : "esc"}</kbd>
      </div>
      {open && (
        <div className="f01-menu">
          {groups.map((group) => (
            <div key={str(group.label)}>
              <div className="f01-menu-heading">{str(group.label)}</div>
              {group.items.map((i) => (
                <button
                  className={items.indexOf(i) === active ? "is-active" : ""}
                  type="button"
                  key={str(i.id)}
                  onClick={() => pick(str(i.id))}
                >
                  {i.icon ? <Glyph name={str(i.icon)} size="sm" /> : null}
                  <span>
                    <Match text={str(i.label)} query={query} />
                  </span>
                  {i.hint ? (
                    <>
                      {" "}
                      <small>{str(i.hint)}</small>
                    </>
                  ) : null}
                  {i.shortcut ? <kbd className="kbd">{str(i.shortcut)}</kbd> : null}
                </button>
              ))}
            </div>
          ))}
          {!items.length && (
            <span className="small">{query ? "No results" : "Type to search"}</span>
          )}
          {name === "CommandPalette" && (
            <>
              <div className="f01-menu-heading">Ask your agent</div>
              <button type="button" onClick={() => send("command.ask", { text: query })}>
                <Avatar label="You" seat="steward" size="xs" />
                <span>
                  <b>“{query}…”</b> ask your agent in words
                </span>
                <kbd className="kbd">↵</kbd>
              </button>
            </>
          )}
        </div>
      )}
      {name === "CommandPalette" && (
        <div className="f01-command-footer">
          <span>
            <kbd className="kbd">↑↓</kbd> move
          </span>
          <span>
            <kbd className="kbd">↵</kbd> run
          </span>
          <span>
            <kbd className="kbd">esc</kbd> close
          </span>
        </div>
      )}
    </div>
  );
}

function Match({ text, query }: { text: string; query: string }) {
  const index = query ? text.toLowerCase().indexOf(query.toLowerCase()) : -1;
  return index < 0 ? (
    text
  ) : (
    <>
      {text.slice(0, index)}
      <b>{text.slice(index, index + query.length)}</b>
      {text.slice(index + query.length)}
    </>
  );
}

export function Filter({ p, send }: ViewProps) {
  const [query, setQuery] = useState(str(p.query));
  useEffect(() => setQuery(str(p.query)), [p.query]);
  return (
    <div className="f01-filter">
      <input
        className="f01-input"
        aria-label="Filter"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          send("filter.change", { query: e.target.value, filters: p.filters });
        }}
      />
      {rows(p.filters).map((f) => (
        <span className="chip chip-on" key={str(f.field)}>
          {str(f.field)} {str(f.op)} {shown(f.value)}
        </span>
      ))}
      <button
        className="btn btn-sm"
        type="button"
        onClick={() =>
          send("sort.change", {
            field: obj(p.sort).field,
            dir: obj(p.sort).dir === "asc" ? "desc" : "asc",
          })
        }
      >
        Sort: {str(obj(p.sort).field, "Updated")}
      </button>
      <span className="small">{shown(p.resultCount)} results</span>
      {p.groupBy ? <span className="chip">Group: {str(p.groupBy)}</span> : null}
    </div>
  );
}
