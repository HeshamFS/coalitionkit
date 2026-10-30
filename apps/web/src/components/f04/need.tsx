// SPDX-License-Identifier: Apache-2.0
import { useId, useState } from "react";
import { Frame, list, number, obj, text, type View } from "../f02/ui";
import "./need.css";

export function NeedForm({ p, send }: View) {
  const id = useId();
  const [value, set] = useState(text(p.text));
  const [quantity, count] = useState(number(p.quantity, 1));
  const [constraints, constrain] = useState(list(p.constraints));
  const [audience, choose] = useState(text(p.audience) || "me");
  const [pending, status] = useState(false);
  const deadline = constraints.find((c) => c.kind === "deadline");
  return (
    <Frame name="NeedForm" state={pending ? "checking" : "draft"}>
      <b className="f04-need-title">What do you need?</b>
      <input
        className="f04-need-input"
        aria-label="Need"
        value={value}
        onChange={(e) => set(e.target.value)}
      />
      <div className="f04-need-grid">
        <label className="f04-need-field" htmlFor={`${id}-deadline`}>
          By
          <input
            id={`${id}-deadline`}
            className="f04-need-input"
            value={text(deadline?.value ?? deadline?.label)}
            onChange={(e) =>
              constrain([
                ...constraints.filter((c) => c.kind !== "deadline"),
                { ...deadline, kind: "deadline", value: e.target.value },
              ])
            }
          />
        </label>
        <div className="f04-need-field">
          <label htmlFor={`${id}-quantity`}>For</label>
          <div className="f04-need-stepper">
            <button
              type="button"
              aria-label="Decrease quantity"
              disabled={quantity <= 1}
              onClick={() => count(quantity - 1)}
            >
              −
            </button>
            <input
              id={`${id}-quantity`}
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => count(Math.max(1, Number(e.target.value) || 1))}
            />
            <button
              type="button"
              aria-label="Increase quantity"
              onClick={() => count(quantity + 1)}
            >
              +
            </button>
          </div>
        </div>
      </div>
      <div className="f04-need-field">
        <span>Who sees it</span>
        <fieldset className="f04-need-segments" aria-label="Who sees it">
          {[
            ["coalition", "Coalition"],
            ["task", "My task"],
            ["me", "Host only"],
          ].map(([scope, label]) => (
            <button
              key={scope}
              type="button"
              aria-pressed={audience === scope}
              onClick={() => choose(scope ?? "me")}
            >
              {label}
            </button>
          ))}
        </fieldset>
      </div>
      <div className="f04-need-note">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 3l8 4v6c0 4-3.5 7-8 8-4.5-1-8-4-8-8V7z" />
        </svg>
        Steward checks it before anyone sees it
      </div>
      <button
        type="button"
        className="ck-action ck-primary"
        disabled={!value.trim() || pending}
        onClick={() => {
          status(true);
          send("coalition.need", {
            text: value,
            quantity: { ...obj(p.quantity), value: quantity },
            constraints,
            audience,
          });
        }}
      >
        Publish need
      </button>
    </Frame>
  );
}
