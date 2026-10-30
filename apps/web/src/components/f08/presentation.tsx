// SPDX-License-Identifier: Apache-2.0
import { createContext } from "react";

/** Form labels and door selection belong to the embedding surface, not vault data. */
export const PrivacyFieldLayout = createContext<{ label?: string; unit?: string }>({});
export const PrivacyDoor = createContext<"wide" | "compact" | "lens">("wide");

/** Optional local-vault previews. These are never part of the model's catalog payload. */
export const DisclosurePreviews = createContext<
  Record<string, { question: string; answer: string; exact: string }>
>({});
/** The embedding surface supplies the current charter, independently of the commitment. */
export const PrivacyCharterRevision = createContext<string | undefined>(undefined);
