// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import { Glyph } from "./Glyph";
import { obj, type Props, rows, shown, str, type ViewProps } from "./shared";

export function Filter({ p, send }: ViewProps) {
  const [query, setQuery] = useState(str(p.query));
  const [filters, setFilters] = useState(rows(p.filters));
  const [direction, setDirection] = useState(str(obj(p.sort).dir, "desc"));
  useEffect(() => setQuery(str(p.query)), [p.query]);
  useEffect(() => setFilters(rows(p.filters)), [p.filters]);
  useEffect(() => setDirection(str(obj(p.sort).dir, "desc")), [p.sort]);
  const update = (next: Props[], q = query) => {
    setFilters(next);
    setQuery(q);
    send("filter.change", { query: q, filters: next });
  };
  return (
    <div className="f01-filter-bar">
      <div className="row wrap">
        <label className="f01-filter-query">
          <Glyph name="search" size="sm" />
          <input
            aria-label="Filter"
            placeholder={str(p.placeholder)}
            value={query}
            onChange={(e) => update(filters, e.target.value)}
          />
        </label>
        {filters.map((f) => (
          <button
            className="chip chip-on"
            type="button"
            key={str(f.field)}
            aria-label={`Remove ${str(f.field)} filter`}
            onClick={() => update(filters.filter((item) => item !== f))}
          >
            <Glyph name="filter" size="sm" />
            {str(f.field)}: {shown(f.value)} ×
          </button>
        ))}
        {rows(p.options).map((group) => (
          <label className="f01-filter-option" key={str(group.field)}>
            <span>{str(group.label, str(group.field))}</span>
            <select
              aria-label={`Filter by ${str(group.field)}`}
              value=""
              onChange={(e) =>
                update([
                  ...filters.filter((f) => f.field !== group.field),
                  { field: group.field, op: "is", value: e.target.value },
                ])
              }
            >
              <option value="">Choose</option>
              {rows(group.options).map((option) => (
                <option key={str(option.value)} value={str(option.value)}>
                  {str(option.label)}
                </option>
              ))}
            </select>
          </label>
        ))}
        <div className="h-right row">
          <span className="small">Sort</span>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => {
              const dir = direction === "asc" ? "desc" : "asc";
              setDirection(dir);
              send("sort.change", { field: obj(p.sort).field, dir });
            }}
          >
            {direction === "desc" ? "Newest first" : "Oldest first"}
            <Glyph name="down" size="sm" />
          </button>
        </div>
      </div>
      <div className="row">
        <span className="small">
          {p.resultLabel ? str(p.resultLabel) : `${shown(p.resultCount)} results`}
        </span>
        {p.groupBy ? <span className="chip">Group: {str(p.groupBy)}</span> : null}
        <button type="button" className="f01-clear" onClick={() => update([], "")}>
          Clear filters
        </button>
      </div>
    </div>
  );
}
