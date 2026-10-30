// SPDX-License-Identifier: Apache-2.0
import type { Props, Send } from "../f08/shared";
import "../../styles/f10.css";

import { Schedule } from "./controls";
export function ScheduleTwin({ p, send }: { p: Props; send: Send }) {
  return <Schedule p={p} send={send} />;
}
