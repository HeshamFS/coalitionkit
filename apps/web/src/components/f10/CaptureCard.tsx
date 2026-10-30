// SPDX-License-Identifier: Apache-2.0
import type { Props, Send } from "../f08/shared";
import "../../styles/f10.css";

import { Capture } from "./controls";
export function CaptureCard({ p, send }: { p: Props; send: Send }) {
  return <Capture p={p} send={send} />;
}
