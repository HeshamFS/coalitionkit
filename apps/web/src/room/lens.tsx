// SPDX-License-Identifier: Apache-2.0
import { LensCard, LensFrame } from "../components/lens";
import type { ViewerState } from "../feed/delta";
import { deriveParticipants } from "../feed/derive";
export function RoomLens({ state }: { state: ViewerState | null }) {
  const own = deriveParticipants(state).find((p) => p.id === state?.viewer);
  return (
    <LensFrame>
      <LensCard
        eyebrow="Your part"
        title={own?.item || "Nothing assigned to you yet"}
        body={own?.agent}
      />
    </LensFrame>
  );
}
