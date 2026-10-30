// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { expired, Frame, label, list, number, obj, text, type View } from "../f02/ui";
import "./details.css";

export function OfferForm({ p, send }: View) {
  const [what, set] = useState(text(p.what));
  const [conditions, update] = useState(list(p.conditions).map(label));
  const [adding, add] = useState(false);
  const [condition, input] = useState("");
  const [amount, cost] = useState(String(number(obj(p.cost).amount)));
  return (
    <Frame name="OfferForm" state="draft">
      <div className="row">
        <span className="small">Offering for</span>
        <span className="chip f04-target">{text(p.target_label) || text(p.target)}</span>
      </div>
      <input
        className="f04-offer-input"
        aria-label="What can you offer?"
        value={what}
        onChange={(e) => set(e.target.value)}
      />
      <label className="field">
        <span>Cost to the group</span>
        <span className="input">
          <span className="mut3">€</span>
          <input
            aria-label="Cost to the group"
            type="number"
            min="0"
            value={amount}
            onChange={(e) => cost(e.target.value)}
          />
          <span className="unit">{obj(p.cost).kind === "quote" ? "quote" : "≈ estimate"}</span>
        </span>
      </label>
      <div className="field">
        <span className="lbl">Conditions</span>
        <div className="row wrap">
          {conditions.map((c, i) => (
            <button
              className="chip chip-on"
              type="button"
              key={String(i)}
              aria-label={`Remove ${c}`}
              onClick={() => update(conditions.filter((_, j) => i !== j))}
            >
              {c}
            </button>
          ))}
          <button className="chip f04-add" type="button" onClick={() => add(!adding)}>
            + add
          </button>
        </div>
        {adding && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (condition.trim()) {
                update([...conditions, condition.trim()]);
                input("");
                add(false);
              }
            }}
          >
            <input
              aria-label="New condition"
              value={condition}
              onChange={(e) => input(e.target.value)}
            />
            <button className="btn btn-sm" type="submit">
              Add
            </button>
          </form>
        )}
      </div>
      <div className="row">
        <span className="scope">{text(p.scope) || text(p.target)}</span>
        <button
          className="btn btn-sm btn-primary f04-push"
          type="button"
          disabled={!what.trim() || !amount || Number(amount) < 0 || expired(p.expires)}
          onClick={() =>
            send("coalition.offer", {
              what,
              target: p.target,
              conditions,
              cost: {
                ...obj(p.cost),
                amount: {
                  value: Number(amount),
                  event_ref: text(obj(obj(p.cost).amount).event_ref),
                },
              },
              expires: p.expires,
            })
          }
        >
          Offer
        </button>
      </div>
    </Frame>
  );
}
