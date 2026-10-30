// SPDX-License-Identifier: Apache-2.0

import type { Props, Send } from "../f08/shared";
import { usePreviewState } from "../f08/shared";
import "../../styles/f11.css";

import { Lessons } from "./controls";
export function LessonReview({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  if (preview === "saved") return <span className="badge b-measured">Lessons saved</span>;
  return <Lessons p={p} send={send} />;
}
