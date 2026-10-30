// SPDX-License-Identifier: Apache-2.0
import { Fields, list, type Props, type Send, text } from "../f08/shared";
import "../../styles/f11.css";
export function SkillCard({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <div className="row">
        <svg className="ico f11-skill-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 2l3 7h7l-5.5 4.5 2 7.5-6.5-4.5-6.5 4.5 2-7.5L2 9h7z" />
        </svg>
        <b className="f11-control-title">{text(p.name)}</b>
        <span className="h-right badge b-estimate">pack draft</span>
      </div>
      <span className="small">
        {list(p.templates).map(text).join(" → ")}
        {list(p.rules).length ? `, ${text(list(p.rules)[0])}.` : "."}
      </span>
      <Fields
        values={{
          Roles: `${list(p.roles).length} members`,
          Tasks: `${list(p.templates).length} templates`,
          Rules: `${list(p.rules).length} from this charter`,
          Source: p.source,
        }}
      />
      <div className="row">
        <button
          type="button"
          className="btn btn-sm"
          aria-label="Start from this skill"
          onClick={() =>
            send("coalition.create", {
              skill: {
                name: p.name,
                source: p.source,
                roles: p.roles,
                rules: p.rules,
                templates: p.templates,
              },
            })
          }
        >
          Start a coalition from it
        </button>
      </div>
    </>
  );
}
