// SPDX-License-Identifier: Apache-2.0
import type { Props, Send } from "../f08/shared";
import "../../styles/f09.css";

import { Masks } from "./controls";
export function MediaWithMasks({ p, send }: { p: Props; send: Send }) {
  return <Masks p={p} send={send} />;
}
