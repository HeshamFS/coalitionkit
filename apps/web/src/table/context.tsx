// SPDX-License-Identifier: Apache-2.0
// What every part of the screen needs, in one place. `answer` is the existing trusted path for a
// consent; nothing built from a composed tree is ever given to it.
import { createContext, useContext } from "react";
import type { ConsentAcknowledgement } from "../components/f08/ConsentSeal";
import type { Answer } from "../feed/actions";
import type { OpenRequest } from "../feed/agent";
import type { ViewerState } from "../feed/delta";
import type { RoomIo } from "./api";
import type { Room } from "./room";

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
  io: RoomIo;
  phone: boolean;
  owner: boolean;
  /** The seat the viewer is looking at as, if any. */
  viewing: string | null;
  openResult: (id: string) => void;
};

export const TableContext = createContext<TableCtx | null>(null);

export function useTable(): TableCtx {
  const ctx = useContext(TableContext);
  if (!ctx) throw new Error("TableContext is missing");
  return ctx;
}
