// SPDX-License-Identifier: Apache-2.0
import { Frame, list, text, type View } from "../f02/ui";
import "./validation.css";

export function ValidationSummary({ p, send }: View) {
  const errors = list(p.errors);
  return (
    <Frame name="ValidationSummary" state="shown">
      <div className="f04-validation-banner" role="alert">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v5M12 16h.01" />
        </svg>
        <div>
          <b>
            {errors.length} {errors.length === 1 ? "thing" : "things"} to fix before sending
          </b>
          <div className="f04-validation-links">
            {errors.map((error) => (
              <button
                type="button"
                key={text(error.field)}
                onClick={() => send("field.focus", { id: error.field })}
              >
                {text(error.text)}
              </button>
            ))}
          </div>
        </div>
      </div>
    </Frame>
  );
}
