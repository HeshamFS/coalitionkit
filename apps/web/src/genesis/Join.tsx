// SPDX-License-Identifier: Apache-2.0
// Joining from a link (story J-04): no token box. The invitation in the link's fragment is
// exchanged for a viewer token and dies.
import { useState } from "react";
import { pinAtJoin } from "../chain/pin";
import { saveToken } from "../feed/config";
import { acceptInvitation, HostError } from "./api";
import { takeInvitation } from "./fragment";
import { TableMark } from "./TableMark";
import "./genesis.css";

export function Join({ onJoined }: { onJoined: () => void }) {
  const [invitation] = useState(() => takeInvitation());
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(
    invitation ? "" : "This link has no invitation in it. Ask for a new link.",
  );
  const join = async () => {
    setBusy(true);
    try {
      const joined = await acceptInvitation(invitation, name);
      saveToken(joined.token);
      pinAtJoin(joined.coalition_id, joined.host_key);
      onJoined();
    } catch (e) {
      setError(
        e instanceof HostError && e.status === 400
          ? "This invitation has been used or withdrawn. Ask for a new link."
          : "The host could not be reached.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="gn-stage gn-join" aria-labelledby="gn-join-title">
      <div className="gn-join-card">
        <TableMark filled={6} lit={false} reading={false} size={96} />
        <h1 id="gn-join-title" className="gn-title">
          You are invited <em>to a coalition.</em>
        </h1>
        <p className="gn-join-p">
          A coalition is a group of people and their agents working toward one goal. You will see
          only your part.
        </p>
        <ul className="gn-join-list">
          <li>
            <b>Others see</b> your seat and what you agree to, after you say yes.
          </li>
          <li>
            <b>Nobody sees</b> your reasons, limits or free time; matching happens without revealing
            them.
          </li>
          <li>
            <b>Nothing commits you</b> until you press and hold to sign.
          </li>
        </ul>
        <form
          className="gn-join-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (invitation && !busy) void join();
          }}
        >
          <label htmlFor="gn-name" className="gn-card-k">
            Your name, as others will see it after you say yes (optional)
          </label>
          <input
            id="gn-name"
            className="gn-inline gn-join-name"
            value={name}
            maxLength={64}
            autoComplete="given-name"
            onChange={(e) => setName(e.target.value)}
          />
          {error && (
            <p className="gn-error" role="alert">
              {error}
            </p>
          )}
          <button type="submit" className="gn-enter" disabled={!invitation || busy}>
            {busy ? "Joining…" : "Join"}
          </button>
        </form>
      </div>
    </main>
  );
}
