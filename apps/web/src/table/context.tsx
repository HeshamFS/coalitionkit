// SPDX-License-Identifier: Apache-2.0
// What every part of the screen needs, in one place. `answer` is the existing trusted path for a
// consent; nothing built from a composed tree is ever given to it.
import { createContext, useContext } from "react";
import type { ConsentAcknowledgement } from "../components/f08/ConsentSeal";
import type { Answer } from "../feed/actions";
import type { OpenRequest } from "../feed/agent";
import type { ViewerState } from "../feed/delta";
import type { AnswerOutcome } from "../feed/useFeed";
import type { CleanupReport, DissolveEvent } from "../moments/Dissolve";
import type { RoomIo, SayReply } from "./api";
import type { Room } from "./room";

/** The last thing said in the box, and where it went: shown on your side, never in the footer. */
export type Said = { text: string; reply?: SayReply; error?: string };

/** How the room ended, when this screen is showing the end after the feed has closed. */
export type Ending = {
  report?: CleanupReport;
  event?: DissolveEvent | null;
  refused?: string;
  pending: boolean;
  onRetry?: () => void;
  onLeave: () => void;
};

export type TableCtx = {
  room: Room;
  state: ViewerState | null;
  /** Every open request the host listed. */
  requests: OpenRequest[];
  /** The ones to show as asks (a plan covered by a choice, or a task by a commitment, is folded). */
  asks: OpenRequest[];
  focus: string | null;
  setFocus: (id: string | null) => void;
  answer: (a: Answer) => Promise<ConsentAcknowledgement | undefined>;
  outcome: (a: Answer, quiet?: boolean) => Promise<AnswerOutcome>;
  io: RoomIo;
  phone: boolean;
  owner: boolean;
  /** The seat the viewer is looking at as, if any. */
  viewing: string | null;
  openResult: (id: string) => void;
  said: Said | null;
  setSaid: (s: Said | null) => void;
  ending?: Ending;
};

export const TableContext = createContext<TableCtx | null>(null);

export function useTable(): TableCtx {
  const ctx = useContext(TableContext);
  if (!ctx) throw new Error("TableContext is missing");
  return ctx;
}
