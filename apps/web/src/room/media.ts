// SPDX-License-Identifier: Apache-2.0
import { useMemo, useSyncExternalStore } from "react";
export function usePhoneRoom() {
  const media = useMemo(() => window.matchMedia?.("(max-width: 640px)"), []);
  return useSyncExternalStore(
    (listener) => {
      media?.addEventListener("change", listener);
      return () => media?.removeEventListener("change", listener);
    },
    () => media?.matches ?? false,
    () => false,
  );
}
