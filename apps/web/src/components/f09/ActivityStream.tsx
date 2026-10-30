// SPDX-License-Identifier: Apache-2.0
import { num, obj, type Props, rows, type Send, text } from "../f08/shared";
import { ActivityStream as LegacyActivityStream } from "./legacy";
import "../../styles/f09.css";

export function ActivityStream({ p, send }: { p: Props; send: Send }) {
  return (
    <LegacyActivityStream
      items={rows(p.items)
        .filter((i) =>
          p.filter === "about me" ? i.aboutMe : p.filter === "decisions" ? i.decision : true,
        )
        .map((i) => ({
          seq: num(i.seq),
          actor: { label: text(obj(i.actor).label ?? i.actor), seat: 1 },
          verb: text(i.verb),
          object: text(i.object),
          time: text(i.time),
          live: Boolean(i.live),
          aboutMe: Boolean(i.aboutMe),
          decision: Boolean(i.decision),
        }))}
      onOpen={(seq) =>
        send("item.open", { seq: rows(p.items).find((i) => num(i.seq) === seq)?.seq })
      }
    />
  );
}
