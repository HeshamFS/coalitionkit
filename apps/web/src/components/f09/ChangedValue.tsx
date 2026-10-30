// SPDX-License-Identifier: Apache-2.0
import { type Props, type Send, text, usePreviewState } from "../f08/shared";
import { ChangedValue as LegacyChangedValue } from "./legacy";
import "../../styles/f09.css";

export function ChangedValue({ p }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  return (
    <LegacyChangedValue
      state={
        preview === "flash" || preview === "tinted" || preview === "seen" ? preview : undefined
      }
      before={text(p.before)}
      after={text(p.after)}
    />
  );
}
