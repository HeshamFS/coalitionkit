// SPDX-License-Identifier: Apache-2.0
import { PreviewState } from "../../components/f08/shared";
import { examples } from "../../components/f10/examples";
import { Family } from "../Cell";
import { One } from "../Drawn";
import "../../styles/f10.css";

const panels = [
  {
    title: "CaptureCard · record the device",
    name: "CaptureCard",
    span: 1,
    props:
      "video (vault) · voice narration · live masks (SAM) with labels · tips: show every control, say units · stop → MintPipeline",
    empty: false,
  },
  {
    title: "MintPipeline · stages and timing",
    name: "MintPipeline",
    span: 3,
    props:
      "stages[] {name, state, took, detail} · elapsed · cost (meter) · artifacts per stage (masks, spec, code) open in a drawer · every stage output is steward-audited",
    empty: false,
  },
  {
    title: "AttackTests · before it goes live",
    name: "AttackTests",
    span: 1,
    props:
      "tests[] {name, kind: bounds | injection | egress | rate | failsafe, state, log} · publish stays locked until all pass",
    empty: false,
  },
  {
    title: "PublishApproval · the owner's yes",
    name: "PublishApproval",
    span: 1,
    props:
      "agent spec {reads[], acts[] with bounds, never[]} · coalitions to join · tests summary · → owner-signed publish · revoke",
    empty: false,
  },
  {
    title: "MintedAgentCard",
    name: "MintedAgentCard",
    span: 1,
    props:
      "agent {name, version, runtime, owner} · readings[] · tools[] · last actions · health · update by re-minting (new version, same pin rules)",
    empty: false,
  },
  {
    title: "EdgeReaderStatus · camera reader",
    name: "EdgeReaderStatus",
    span: 1,
    props:
      "source: camera | serial | vendor app · rate · confidence · frames retained (default none) · fallback rule",
    empty: false,
  },
  {
    title: "DeviceReading · time series",
    name: "DeviceReading",
    span: 2,
    props:
      "series[] {t, value, confidence} · unit · planned? · limits[] · annotations[] (task events) · source agent · table alternative",
    empty: false,
  },
  {
    title: "DeviceAlarm · out of range",
    name: "DeviceAlarm",
    span: 1,
    props:
      "device · reading · threshold · duration · autoAction (within bounds) · actions: stop | acknowledge · ripples affected tasks",
    empty: false,
  },
  {
    title: "ScheduleTwin · device time",
    name: "ScheduleTwin",
    span: 1,
    props:
      "machines[] {name, owner, bookings[] {start, end, mine?}} · other bookings shown as busy only · hold → offer",
    empty: false,
  },
];
function Panel({ panel }: { panel: (typeof panels)[number] }) {
  const example = examples.find((e) => e.name === panel.name);
  const state = panel.empty ? example?.states.find((s) => s.state === "empty") : example?.states[0];
  return (
    <div className={`cell${panel.span > 1 ? ` span${panel.span}` : ""}`} data-panel={panel.title}>
      <div className="head">
        <span className="cell-name">{panel.title}</span>
      </div>
      <div className="demo">
        {state && (
          <PreviewState value={state.state}>
            <One component={panel.name} props={state.props} />
          </PreviewState>
        )}
      </div>
      <div className="props">{panel.props}</div>
    </div>
  );
}
export function Sheet10() {
  return (
    <div className="sheet sheet-10" data-testid="sheet-10">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 10 · example data</div>
          <div className="sheet-title">Mint, devices and agents</div>
          <div className="sheet-sub">
            Turning a device that has no API into an agent from a video and a voice note, and
            watching that agent’s readings.
          </div>
        </div>
        <div className="h-right">
          <span className="badge b-example">Example data</span>
        </div>
      </div>
      <Family n="10a" title="Mint: from a recording to a live agent">
        {panels.slice(0, 6).map((panel) => (
          <Panel key={panel.title} panel={panel} />
        ))}
      </Family>
      <Family n="10b" title="Devices: readings, alarms and schedule">
        {panels.slice(6, 9).map((panel) => (
          <Panel key={panel.title} panel={panel} />
        ))}
      </Family>
      <details className="family-extra">
        <summary>Additional catalog states</summary>
        {examples.map((example) => (
          <div key={example.name}>
            {example.states.slice(example.name === "CoalitionArchive" ? 2 : 1).map((state) => (
              <PreviewState key={state.state} value={state.state}>
                <One component={example.name} props={state.props} />
              </PreviewState>
            ))}
          </div>
        ))}
      </details>
    </div>
  );
}
