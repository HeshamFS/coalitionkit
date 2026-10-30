// SPDX-License-Identifier: Apache-2.0
import { Action, type Props, type Send, Table, text } from "./shared";
import "../../styles/f08.css";

export function VaultCard({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <div className="row">
        <b>Your vault</b>
        <span className="h-right st">{text(p.location)} · encrypted</span>
      </div>
      <Table data={p.categories} columns={["name", "count", "policy"]} />
      <span className="small">Answered {text(p.answersToday)} questions today</span>
      <div className="row">
        <Action label="Export" event="vault.export" send={send} />
        <Action label="Wipe vault" event="vault.wipe" send={send} />
      </div>
    </>
  );
}
