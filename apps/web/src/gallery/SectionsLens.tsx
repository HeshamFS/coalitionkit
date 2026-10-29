// SPDX-License-Identifier: Apache-2.0
import { LensCard, LensFrame } from "../components/lens";
import { Cell } from "./Cell";

const tapNext = [
  { gesture: "Tap" as const, does: "got it" },
  { gesture: "Swipe" as const, does: "next", tone: "muted" as const },
];

/** The lens door, drawn at its real 600 x 600 size: one card, one step, black is transparent. */
export function Lens() {
  return (
    <>
      <div className="fam" data-testid="gallery-lens">
        <span className="fam-n">09b</span>
        <span className="fam-t">Glasses · lens door</span>
        <span className="fam-line" />
      </div>
      <div className="g2">
        <Cell
          name="LensCard"
          doors={["lens"]}
          props="title (22 px or more) · eyebrow? · body? (one line) · gestures: 0 to 2 · states: shown, acknowledged · min text 20 px at 600 px, no scroll, no hover"
          events="gesture(name): tap confirms, swipe moves on; a decision is made on the phone"
        >
          <div className="caps">Real size · 600 × 600 · step 1 of 3</div>
          <LensFrame label="Lens frame, information step">
            <LensCard
              eyebrow="Gather"
              title="Goal 1"
              body="3 members"
              step={{ index: 0, total: 3 }}
              hints={tapNext}
            />
          </LensFrame>
        </Cell>
        <Cell
          name="LensCard · ask"
          doors={["lens"]}
          props="the same card for a request: decisions stay on the phone, the lens only shows it"
          events="lens.next · lens.dismiss; nothing is answered from the lens"
        >
          <div className="caps">Step 3 of 3 · asks you</div>
          <LensFrame label="Lens frame, request step">
            <LensCard
              eyebrow="Asks you · 1 of 1"
              title="Take Plan A?"
              body="Decide on your phone"
              step={{ index: 2, total: 3 }}
              hints={tapNext}
            />
          </LensFrame>
        </Cell>
      </div>
    </>
  );
}
