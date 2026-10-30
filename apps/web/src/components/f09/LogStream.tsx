// SPDX-License-Identifier: Apache-2.0
import { list, num, type Props, rows, type Send, text } from "../f08/shared";
import { LogStream as LegacyLogStream } from "./legacy";
import "../../styles/f09.css";

export function LogStream({ p, send }: { p: Props; send: Send }) {
  return (
    <LegacyLogStream
      entries={rows(p.entries)
        .filter((e) => !list(p.filter).length || list(p.filter).includes(e.type))
        .map((e) => ({
          seq: num(e.seq),
          ts: text(e.ts),
          type: text(e.type),
          summary: text(e.summary),
          hash: text(e.hash),
          form: e.form === "projection" || e.form === "receipt-only" ? e.form : "original",
        }))}
      onOpen={(seq) =>
        send("entry.open", { seq: rows(p.entries).find((e) => num(e.seq) === seq)?.seq })
      }
    />
  );
}
