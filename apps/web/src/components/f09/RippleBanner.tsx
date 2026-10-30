// SPDX-License-Identifier: Apache-2.0
import type { Props, Send } from "../f08/shared";
import "../../styles/f09.css";

import { Ripple } from "./controls";
export function RippleBanner({ p, send }: { p: Props; send: Send }) {
  return <Ripple p={p} send={send} />;
}
