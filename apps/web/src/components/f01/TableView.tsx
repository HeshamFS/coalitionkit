// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import { DataCell } from "./DataCell";
import { number, obj, type Props, rows, str, type ViewProps } from "./shared";

export function TableView({ p, send }: Pick<ViewProps, "p" | "send">) {
  const [selected, setSelected] = useState<string[]>(
    Array.isArray(p.selected) ? p.selected.map((v) => str(v)) : [],
  );
  useEffect(
    () => setSelected(Array.isArray(p.selected) ? p.selected.map((v) => str(v)) : []),
    [p.selected],
  );
  const page = Math.max(1, number(p.page, 1));
  const items = rows(p.rows).slice(0, Math.max(1, number(p.pageSize, 1000)));
  const columns = rows(p.columns);
  const selectable = p.selection === "one" || p.selection === "many";
  const choose = (ids: string[]) => {
    setSelected(ids);
    send("select", { ids });
  };
  return (
    <div className="col">
      <div className="f01-table-scroll">
        <table className="f01-table">
          <thead>
            <tr>
              {selectable && (
                <th className="f01-table-check">
                  {p.selection === "many" && (
                    <input
                      type="checkbox"
                      aria-label="Select all rows"
                      checked={!!items.length && items.every((r) => selected.includes(str(r.id)))}
                      onChange={(e) => choose(e.target.checked ? items.map((r) => str(r.id)) : [])}
                    />
                  )}
                </th>
              )}
              {columns.map((c) => (
                <th key={str(c.key)} style={{ textAlign: c.align === "right" ? "right" : "left" }}>
                  {p.sortable && c.sortable !== false ? (
                    <button type="button" onClick={() => send("sort", { key: c.key })}>
                      {str(c.label)}{" "}
                      {c.direction === "desc" ? "↓" : c.direction === "asc" ? "↑" : "↕"}
                    </button>
                  ) : (
                    str(c.label)
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((r, i) => (
              <TableRow
                key={str(r.id, String(i))}
                row={r}
                columns={columns}
                selected={selected.includes(str(r.id))}
                selectable={selectable}
                open={() => send("open", { row: r })}
                choose={() =>
                  choose(
                    selected.includes(str(r.id))
                      ? selected.filter((id) => id !== r.id)
                      : p.selection === "one"
                        ? [str(r.id)]
                        : [...selected, str(r.id)],
                  )
                }
              />
            ))}
          </tbody>
        </table>
        {!items.length && <span className="small">No rows</span>}
      </div>
      {(selectable || p.total !== undefined) && (
        <div className="row f01-table-footer">
          {selectable && <span className="small">{selected.length} selected</span>}
          {obj(p.action).label ? (
            <button
              type="button"
              className="btn btn-sm"
              disabled={!selected.length}
              onClick={() => send("table.action", { ids: selected })}
            >
              {str(obj(p.action).label)}
            </button>
          ) : null}
          {p.total !== undefined && (
            <span className="h-right small">
              {items.length ? (page - 1) * number(p.pageSize, items.length) + 1 : 0}–
              {(page - 1) * number(p.pageSize, items.length) + items.length} of {number(p.total)}{" "}
              <button
                type="button"
                className="kbd"
                aria-label="Previous page"
                disabled={page === 1}
                onClick={() => send("table.page", { page: page - 1 })}
              >
                ‹
              </button>{" "}
              <button
                type="button"
                className="kbd"
                aria-label="Next page"
                disabled={page * number(p.pageSize, items.length) >= number(p.total)}
                onClick={() => send("table.page", { page: page + 1 })}
              >
                ›
              </button>
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function TableRow({
  row,
  columns,
  selected,
  selectable,
  open,
  choose,
}: {
  row: Props;
  columns: Props[];
  selected: boolean;
  selectable: boolean;
  open: () => void;
  choose: () => void;
}) {
  return (
    <tr aria-selected={selectable ? selected : undefined}>
      {selectable && (
        <td className="f01-table-check">
          <input
            type="checkbox"
            aria-label={`Select ${str(row[str(columns[0]?.key)], str(row.id))}`}
            checked={selected}
            onChange={choose}
          />
        </td>
      )}
      {columns.map((c, i) => (
        <td
          key={str(c.key)}
          style={{ textAlign: c.align === "right" ? "right" : "left" }}
          className={c.align === "right" || c.key === "when" ? "mono" : undefined}
        >
          {i === 0 ? (
            <button type="button" onClick={open}>
              <DataCell value={row[str(c.key)]} format={str(c.format)} />
            </button>
          ) : (
            <DataCell value={row[str(c.key)]} format={str(c.format)} />
          )}
        </td>
      ))}
    </tr>
  );
}
