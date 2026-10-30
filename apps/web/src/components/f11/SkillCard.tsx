// SPDX-License-Identifier: Apache-2.0
import { Action, Fields, type Props, type Send, text } from "../f08/shared";
import "../../styles/f11.css";

export function SkillCard({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <b>{text(p.name)}</b>
      <span className="st">from {text(p.source)}</span>
      <Fields values={{ Roles: p.roles, Rules: p.rules, Templates: p.templates }} />
      <Action
        label="Start from this skill"
        event="coalition.create"
        send={send}
        data={{
          skill: {
            name: p.name,
            source: p.source,
            roles: p.roles,
            rules: p.rules,
            templates: p.templates,
          },
        }}
        primary
      />
    </>
  );
}
