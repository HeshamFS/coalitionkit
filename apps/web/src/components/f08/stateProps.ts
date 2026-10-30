// SPDX-License-Identifier: Apache-2.0
import { num, obj, type Props, rows } from "./shared";

const bound = (value: number) => ({ value, event_ref: "example:1" });
/** Gallery-only state fixtures. Production values always come from the host. */
export function stateProps(name: string, state: string, p: Props): Props {
  const next = { ...p };
  if (name === "CanaryMonitor") next.found = bound(state === "leak" ? 1 : 0);
  if (name === "PrivateField" && state === "revealed") next.display = "€140";
  if (name === "OverlapView" && state === "running") {
    delete next.result;
    next.tokens = [];
  }
  if (name === "CanvasPresence" && state === "idle") next.cursors = [];
  if (name === "ChainView")
    next.entries = rows(p.entries).map((e, i) => ({
      ...e,
      verified: state !== "broken" || i !== 1,
    }));
  if (name === "EvidenceCard") next.masks = state === "masked" ? ["private region"] : [];
  if (name === "GardenerThinking")
    next.steps = rows(p.steps).map((s, i) => ({
      ...s,
      state:
        state === "running" && i === 2
          ? "running"
          : state === "failed" && i === 2
            ? "failed"
            : "done",
    }));
  if (name === "MediaWithMasks" && state === "loading") {
    delete next.media_ref;
    next.masks = [];
    next.labels = [];
  }
  if (name === "StepProgress")
    next.progress = bound(state === "done" ? 1 : state === "deviating" ? 0.42 : 0.64);
  if (name === "StewardVerdict") next.verdict = { ...obj(p.verdict), action: state };
  if (name === "VerifyPanel")
    next.checks = rows(p.checks).map((c, i) => ({ ...c, state: i === 0 ? state : "passed" }));
  if (name === "AttackTests")
    next.tests = rows(p.tests).map((t, i) => ({
      ...t,
      state: state === "passed" || i !== 3 ? "passed" : state,
    }));
  if (name === "MintPipeline")
    next.stages = rows(p.stages).map((s, i) => ({
      ...s,
      state: state === "ready to publish" ? "done" : i === 2 ? state : i < 2 ? "done" : "waiting",
    }));
  if (name === "DeviceAlarm" && state === "cleared") next.reading = bound(num(p.threshold) - 1);
  return next;
}
