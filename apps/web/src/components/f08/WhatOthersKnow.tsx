// SPDX-License-Identifier: Apache-2.0
import { Action, type Props, type Send, Table } from "./shared";
import "../../styles/f08.css";

export function WhatOthersKnow({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <Table data={p.rows} columns={["participant", "knows", "notKnows", "because"]} />
      <Action label="Export this view" event="view.export" send={send} />
    </>
  );
}
