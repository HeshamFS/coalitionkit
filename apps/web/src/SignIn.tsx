// SPDX-License-Identifier: Apache-2.0
import { type FormEvent, useState } from "react";
import { Banner } from "./components/feedback";
import { saveToken } from "./feed/config";
import { Icon } from "./ui/Icon";

/** The sign-in step: the viewer pastes the token from the invitation. It is never read from the address. */
export function SignIn({ onDone, notice }: { onDone: () => void; notice?: string }) {
  const [value, setValue] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const token = value.trim();
    if (!token) return;
    saveToken(token);
    onDone();
  };
  return (
    <form
      onSubmit={submit}
      className="card"
      style={{ maxWidth: 420, margin: 24 }}
      aria-label="Sign in"
    >
      <div className="row">
        <Icon name="lock" />
        <b>Sign in</b>
      </div>
      {notice && <Banner tone="ask" title={notice} />}
      <div className="field">
        <label htmlFor="ck-token">Viewer token</label>
        <input
          id="ck-token"
          className="input"
          type="password"
          autoComplete="off"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <span className="help">Paste the token from your invitation. It stays in this tab.</span>
      </div>
      <div className="row">
        <button type="submit" className="btn btn-primary" disabled={!value.trim()}>
          Continue
        </button>
      </div>
    </form>
  );
}
