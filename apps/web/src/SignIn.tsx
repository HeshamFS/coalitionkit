// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { saveToken } from "./feed/config";
import { TableMark } from "./genesis/TableMark";
import "./genesis/genesis.css";

/** The developer fallback: paste a viewer token. It is never read from the address. */
export function SignIn({ onDone, notice }: { onDone: () => void; notice?: string }) {
  const [value, setValue] = useState("");
  return (
    <main className="gn-stage gn-join" aria-labelledby="ck-signin-title">
      <form
        className="gn-join-card"
        aria-label="Sign in"
        onSubmit={(e) => {
          e.preventDefault();
          const token = value.trim();
          if (!token) return;
          saveToken(token);
          onDone();
        }}
      >
        <TableMark filled={7} lit={false} reading={false} size={72} />
        <h1 id="ck-signin-title" className="gn-title">
          Have a token?
        </h1>
        {notice && (
          <p className="gn-error" role="alert">
            {notice}
          </p>
        )}
        <label htmlFor="ck-token" className="gn-card-k">
          Viewer token
        </label>
        <input
          id="ck-token"
          className="gn-inline gn-join-name"
          type="password"
          autoComplete="off"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <span className="gn-card-meta">
          Paste the token from your invitation. It stays in this tab.
        </span>
        <button type="submit" className="gn-enter" disabled={!value.trim()}>
          Continue
        </button>
        <a className="gn-link" href="/">
          Start a coalition instead
        </a>
      </form>
    </main>
  );
}
