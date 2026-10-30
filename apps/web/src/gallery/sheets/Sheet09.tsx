// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from "react";
import { PreviewState } from "../../components/f08/shared";
import { bound, errors, sheetSamples } from "../../components/f09/sheetSamples";
import { Family } from "../Cell";
import { One } from "../Drawn";
import "../../styles/f09.css";

function Sample({ name }: { name: string }) {
  return <One component={name} props={sheetSamples[name] ?? {}} />;
}
function Panel({
  title,
  props,
  span,
  accessory,
  children,
}: {
  title: string;
  props: string;
  span?: boolean;
  accessory?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className={`cell${span ? " span2" : ""}`} data-panel={title}>
      <div className="head">
        <span className="cell-name">{title}</span>
        {accessory && <span className="h-right">{accessory}</span>}
      </div>
      <div className="demo">{children}</div>
      <div className="props">{props}</div>
    </div>
  );
}
function Doors({ names }: { names: string[] }) {
  return (
    <span className="door">
      {names.map((name) => (
        <span key={name}>{name}</span>
      ))}
    </span>
  );
}
function RipplePanel() {
  return (
    <Panel
      title="RippleBanner · ChangedValue"
      span
      accessory={<Doors names={["wide", "compact", "lens"]} />}
      props="ripple {by, change, invalidated[], untouched[]} · ChangedValue {path, before, after} · flash once · tint until seen · from STATE_DELTA ops on this viewer's projection"
    >
      <Sample name="RippleBanner" />
      <div className="g3 f09-task-grid">
        <div className="card card-live">
          <span className="h-title">t2 · Transfer to A</span>
          <div className="small f09-inline">
            leaves{" "}
            <PreviewState value="flash">
              <One
                component="ChangedValue"
                props={{ path: "/tasks/t2/time", before: "16:00", after: "17:00" }}
              />
            </PreviewState>
          </div>
          <span className="tag t-changed">Changed</span>
        </div>
        <div className="card card-live">
          <span className="h-title">t3 · Process</span>
          <div className="small f09-inline">
            starts{" "}
            <PreviewState value="flash">
              <One
                component="ChangedValue"
                props={{ path: "/tasks/t3/time", after: "Thu 10:00" }}
              />
            </PreviewState>
          </div>
          <span className="tag t-changed">Changed</span>
        </div>
        <div className="card f09-untouched">
          <span className="h-title">t1 · Prepare</span>
          <span className="small">done · not affected</span>
          <span className="tag t-agreed">Agreed</span>
        </div>
      </div>
      <div className="row small">
        <span className="row">
          <span className="flash" style={{ padding: "0 6px" }}>
            value
          </span>
          flashes once, 900 ms, then stays tinted until you look
        </span>
        <span className="h-right st">reduced motion: tint only</span>
      </div>
    </Panel>
  );
}
function LivePanels() {
  return (
    <Family n="09a" title="Live: ripple, activity and presence">
      <RipplePanel />
      <Panel
        title="ActivityStream"
        props="items[] {actor, verb, object, time, seq} · filters · each item opens its log entry · only events in the viewer's projection"
      >
        <Sample name="ActivityStream" />
      </Panel>
      <Panel
        title="GardenerThinking · planning steps"
        props="steps[] {name, state: done | running | next, took} · actor · never shows candidate plans before the steward passes them"
      >
        <Sample name="GardenerThinking" />
      </Panel>
      <Panel
        title="CanvasPresence · agents at work"
        span
        accessory={<Doors names={["wide"]} />}
        props="cursors[] {actor, kind: person | agent, target, verb} · dashed outline = an agent is working on it · shows only while acting · from TOOL_CALL and presence, never invented"
      >
        <Sample name="CanvasPresence" />
      </Panel>
      <Panel
        title="ConnectionStatus · LiveDocks"
        props="feed: live | reconnecting | offline · run id · latency · docks[] {icon, label, value, ref} · RUN_ERROR keeps the last good surface"
      >
        <div className="col">
          {["live", "reconnecting", "offline"].map((feed) => (
            <One
              key={feed}
              component="ConnectionStatus"
              props={{ feed, run: "4", latencyMs: bound(12) }}
            />
          ))}
          <Sample name="LiveDocks" />
        </div>
      </Panel>
      <Panel
        title="StepProgress · a task in motion"
        accessory={<span className="badge b-measured">device</span>}
        props="task · planned curve · measured series (source device) · progress · ETA · deviations flagged by tolerance"
      >
        <Sample name="StepProgress" />
      </Panel>
    </Family>
  );
}
const provenance = [
  ["measured", "a device or a run produced it"],
  ["vault", "a vault answered; the value stayed"],
  ["signed", "a key signed it; check it yourself"],
  ["model", "a model wrote it; may be wrong"],
  ["estimate", "a forecast or quote, not a charge"],
];
function ProofPanels() {
  return (
    <Family n="09b" title="Proof: the log, the chain, the receipts">
      <Panel
        title="LogStream · EventRow"
        span
        accessory={<Doors names={["wide"]} />}
        props="entries[] {seq, ts, type, actor, summary, hash, form: original | projection | receipt-only} · gaps never hidden · tap → WiringDrawer"
      >
        <Sample name="LogStream" />
      </Panel>
      <Panel
        title="ChainView · hash-linked entries"
        span
        accessory={<span className="badge b-signed">host ed25519</span>}
        props="entries[] {seq, type, actor, prev_hash, hash, verified} · first broken link highlighted · genesis from coalition id, host key, created_at"
      >
        <Sample name="ChainView" />
      </Panel>
      <Panel
        title="ReceiptBadge · ProvenanceTag"
        props="ReceiptBadge {seq, state: ok | bad | pending} · ProvenanceTag {kind, source ref} · every number on a surface carries one (bound to its event)"
      >
        <div className="row wrap">
          {["ok", "bad", "pending"].map((state) => (
            <One key={state} component="ReceiptBadge" props={{ state, seq: bound(54) }} />
          ))}
        </div>
        <div className="hr" />
        <div className="col f09-provenance">
          {provenance.map(([kind, detail]) => (
            <div className="row small" key={kind}>
              <One component="ProvenanceTag" props={{ kind, source: "example:1" }} />
              {detail}
            </div>
          ))}
        </div>
      </Panel>
      <Panel
        title="StewardVerdict · signed"
        props="verdict {event_id, revision, action, policy_id, redact[], explain, model_audited, issued_at, sig} · escalate = a person looks"
      >
        <Sample name="StewardVerdict" />
      </Panel>
      <Panel
        title="EvidenceCard · proof a task was done"
        props="kind · ref · task · verified_by · masks? · captured_at · shown in the viewer's scope only"
      >
        <Sample name="EvidenceCard" />
      </Panel>
      <Panel
        title="MediaWithMasks · SAM regions"
        accessory={<span className="badge b-model">masks: model</span>}
        props="media_ref · masks[] {polygon | rle, label, score} · hidden[] (redacted regions) · labels editable by the owner · frame index for video"
      >
        <Sample name="MediaWithMasks" />
      </Panel>
      <Panel
        title="VerifyPanel · check it yourself"
        span
        props="checks[] {name, state, detail} · runs in the browser with the contracts library · export: log + receipts + host key · same result offline (CLI)"
      >
        <Sample name="VerifyPanel" />
      </Panel>
      <Panel
        title="ErrorNotice · protocol errors in words"
        span
        props="code (from the spec's error table) → plain sentence + what happens next · detail · ref (event) · never a raw stack trace"
      >
        <div className="g2 f09-errors">
          {errors.map(([code, message]) => (
            <One
              key={code}
              component="ErrorNotice"
              props={{ code, detail: { message, retry: false } }}
            />
          ))}
        </div>
      </Panel>
    </Family>
  );
}
export function Sheet09() {
  return (
    <div className="sheet f09-sheet" data-testid="sheet-09">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 09 · example data</div>
          <div className="sheet-title">Live and proof</div>
          <div className="sheet-sub">
            What moves while you watch, and how you check any of it: only what changed lights up,
            agents show where they work, and every value leads back to a signed entry in a log
            anyone in the coalition can verify.
          </div>
        </div>
        <div className="h-right">
          <span className="badge b-example">Example data</span>
          <span className="scope">STATE_DELTA · STEP_* · log · receipts</span>
        </div>
      </div>
      <LivePanels />
      <ProofPanels />
    </div>
  );
}
