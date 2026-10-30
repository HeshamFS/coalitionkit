// SPDX-License-Identifier: Apache-2.0
// Shapes every family's Zod APIs share. Text props accept a literal or a {path} binding; numbers
// are only ever {value, event_ref}; events are named, never code. The APIs live in ./families.
import { z } from "zod";

export const Bound = z
  .object({ value: z.number().finite(), event_ref: z.string().min(1) })
  .strict();
// Plain numbers never travel as numbers (the host rejects an unbound number), so seats, gaps and
// column counts are strings on the wire and turned into numbers by the implementation.
export const Seat = z.enum(["1", "2", "3", "4", "5", "host", "steward"]);
export const Gap = z.enum(["4", "8", "12", "16"]);
