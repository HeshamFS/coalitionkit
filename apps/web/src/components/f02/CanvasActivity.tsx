// SPDX-License-Identifier: Apache-2.0
import { label, list, number, obj, text } from "./ui";

/** Viewer-projected activity uses canvas coordinates supplied with presence. */
export function CanvasActivity({ presence }: { presence: unknown }) {
  return (
    <div className="f02-canvas-activity">
      {list(presence).map((person) => {
        const cursor = obj(person.cursor);
        if (!Object.keys(cursor).length) return null;
        const connection = obj(cursor.connection);
        const from = obj(connection.from);
        const to = obj(connection.to);
        const x = number(from.x),
          y = number(from.y),
          endX = number(to.x),
          endY = number(to.y);
        const bend = y + (endY - y) * 0.55;
        const seat = Math.max(1, Math.min(5, number(cursor.seat, 1)));
        return (
          <div key={text(person.id) || label(person)}>
            {Boolean(connection.from && connection.to) && (
              <svg className="f02-activity-link" aria-hidden="true">
                <path d={`M${x} ${y} C${x} ${bend}, ${endX - 5} ${bend}, ${endX} ${endY}`} />
              </svg>
            )}
            <div
              className="f02-activity-cursor"
              style={{
                left: number(cursor.x),
                top: number(cursor.y),
                color: `var(--seat-${seat})`,
              }}
            >
              <svg width="14" height="16" viewBox="0 0 14 16" aria-hidden="true">
                <path d="M1 1l11 6-5 1.5L5 14z" fill="currentColor" />
              </svg>
              <span style={{ background: `var(--seat-${seat})` }}>
                {text(cursor.label) || label(person)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
