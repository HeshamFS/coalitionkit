// SPDX-License-Identifier: Apache-2.0
import { Badge, obj, type Props, rows, type Send, text } from "./shared";
export function ProjectionNote({ p, send }: { p: Props; send: Send }) {
  const source = obj(p.source);
  return (
    <>
      <div className="head">
        {Boolean(source.label) && <span className="h-title">{text(source.label)}</span>}
        <span className="h-right">
          <Badge tone="signed">projection</Badge>
        </span>
      </div>
      <dl className="kv" style={{ fontSize: 12 }}>
        {rows(source.fields).map((f) => (
          <div className="f08-projection-field" key={text(f.label)}>
            <dt>{text(f.label)}</dt>
            <dd>
              {f.hidden ? (
                <>
                  <span className="redact" style={{ width: 60 }} /> {text(p.removed)} hidden
                </>
              ) : (
                text(f.value)
              )}
            </dd>
          </div>
        ))}
      </dl>
      <button
        type="button"
        aria-label="Verify projection"
        className="banner bn-info f08-verify"
        onClick={() => send("projection.verify", { source: p.source })}
      >
        <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 11v5M12 8h.01" />
        </svg>
        <span>
          The host signed this version for you. It links to the original by hash, so you can prove
          it wasn't altered.
        </span>
      </button>
    </>
  );
}
