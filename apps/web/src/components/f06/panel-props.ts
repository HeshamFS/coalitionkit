// SPDX-License-Identifier: Apache-2.0
export const panelProps: Record<string, string> = {
  NeedCard:
    "need_id · owner · text · constraints[] · by · state: open | matched | fulfilled | withdrawn · offers count · task?",
  OfferCard:
    "offer_id · target (need | task) · what · cost {amount, kind} · conditions[] · expires · state: open | accepted | expired | withdrawn · scope",
  AnswerCard:
    "query · kind: bool | number-range | choice · answer · from vault · task_id? · state: waiting | answered | declined",
  MatchView:
    "need · offers[] {offer, fit, reasons[], blockedBy?} · chosen · lines: chosen | possible | fails",
  TaskCard:
    "task_id · title · assignee · window · status (6 + withdrawn) · deps {waitsFor[], unblocks[]} · evidence? · revision",
  Gantt:
    "rows[] {task, assignee, start, end, status} · now · deadlines[] · criticalPath[] · zoom: hours | days | weeks · compact door → Timeline list",
  DependencyGraph:
    "nodes[] {task, status} · edges[] {from, to} · changed · invalidated[] (from ripple payload) · untouched shown grey",
  Checklist:
    "items[] {text, done, by?, evidence?} · owner-only edits · ticks are not protocol events until done is sent",
  Timeline:
    "items[] {start, end?, title, assignee, state} · now marker · groups by day · the compact form of Gantt",
  PlanCompare:
    "plans[] {id, label, objectives {name: value, unit, better: lower | higher}, assignments[] (only yours, unless public), tags[]} · rejected[] {plan, reason} · proposal_set_id · decision_deadline",
  AssignmentRow:
    "assignments[] (viewer's own, from the viewer-specific projection) · hours · share · vault fit check",
  TensionCard:
    "tension_id · task_ids[] · options[] {id, label, tradeoffs[]} · deciders[] · answers (counts only until closed) · decision_deadline · a split re-plans",
  FairnessMeter:
    "rows[] {participant, hours, share, agreedShare} · cap (from charter) · over-cap rows turn ask tone and name the rule",
  CostSplit:
    "items[] {label, payer, amount, kind: quote | estimate} · rule: even | by share | by use · settlements[] (v0.2 pays; v0.1 shows only)",
};
