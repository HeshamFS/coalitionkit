// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { overlapFrom, rippleFrom, theatreFrom } from "./adapters";
import { momentsFixture } from "./fixture";
import { Overlap } from "./Overlap";
import { Ripple } from "./Ripple";
import { Theatre } from "./Theatre";

const OWN_VAULT = ["slot 1", "slot 2", "slot 3"];

/** Review page: the three moments on neutral fixture data. Not routed. */
export function MomentsDemo() {
  const [shown, setShown] = useState(false);
  const result = shown ? { shared: "slot 2", keptPrivate: 2 } : undefined;
  return (
    <div style={{ display: "grid", gap: 24, padding: 16 }}>
      <Theatre {...theatreFrom(momentsFixture)} />
      <div style={{ display: "grid", gap: 8 }}>
        <Overlap {...overlapFrom(momentsFixture, { vault: OWN_VAULT, theirCount: 3, result })} />
        <button type="button" onClick={() => setShown((v) => !v)} style={{ justifySelf: "start" }}>
          {shown ? "Hide the result channel" : "Simulate the result arriving on my own channel"}
        </button>
      </div>
      <Ripple {...rippleFrom(momentsFixture)} />
    </div>
  );
}
