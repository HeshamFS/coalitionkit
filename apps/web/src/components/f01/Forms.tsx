// SPDX-License-Identifier: Apache-2.0
import { useEffect, useId, useState } from "react";
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
        <div className="row">
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
            min={number(p.min)}
            max={p.max ? number(p.max) : undefined}
            step={number(p.step, 1)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && name === "TextField") send("submit", { value });
            }}
          />
          {p.unit ? <span className="small">{str(p.unit)}</span> : null}
        </div>
      )}
      {p.tz ? <span className="small">{str(p.tz)}</span> : null}
      {error && (
        <span id={`${id}-error`} className="f01-error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}

export function Toggle({ name, p, send }: ViewProps) {
  const [value, setValue] = useState(Boolean(p.value));
  useEffect(() => setValue(Boolean(p.value)), [p.value]);
  return (
    <label className="f01-toggle">
      <input
        type="checkbox"
        role={name === "Switch" ? "switch" : undefined}
        checked={value}
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
  if (p.display === "menu")
    return (
      <select
        className="f01-input"
        aria-label="Choose an option"
        value={str(value)}
        onChange={(e) => pick(e.target.value)}
      >
        <option value="">Choose…</option>
        {options.map((o) => (
          <option key={str(o.id)} value={str(o.id)} disabled={!!o.disabled}>
            {str(o.label)}
          </option>
        ))}
      </select>
    );
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
  const items = rows(obj(p.query).groups ?? p.groups)
    .flatMap((g) => rows(g.items))
    .filter((i) => str(i.label).toLowerCase().includes(query.toLowerCase()));
  const pick = (id: string) =>
    send(name === "CommandPalette" ? "command.run" : "search.pick", { id });
  return (
    <div className="f01-search">
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
      {open && (
        <div className="f01-menu">
          {items.map((i, index) => (
            <button
              className={index === active ? "is-active" : ""}
              type="button"
              key={str(i.id)}
              onClick={() => pick(str(i.id))}
            >
              {str(i.label)}
            </button>
          ))}
          {!items.length && (
            <span className="small">{query ? "No results" : "Type to search"}</span>
          )}
          {name === "CommandPalette" && (
            <button type="button" onClick={() => send("command.ask", { text: query })}>
              Ask your agent: {query}
            </button>
          )}
        </div>
      )}
    </div>
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
    </div>
  );
}
