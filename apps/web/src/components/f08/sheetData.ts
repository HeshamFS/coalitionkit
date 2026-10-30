// SPDX-License-Identifier: Apache-2.0
import { obj, type Props } from "./shared";

const bound = (value: number) => ({ value, event_ref: "example:1" });
export function sheetData(name: string, state: string, p: Props): Props {
  if (name === "ProjectionNote")
    return {
      ...p,
      source: {
        ...obj(p.source),
        label: "Plan A · finish Wednesday",
        fields: [
          { label: "Your tasks", value: "t2, t4, t5" },
          { label: "Others' tasks", hidden: true },
          { label: "Total cost", value: "€158" },
        ],
      },
    };
  if (name === "OverlapView" && state === "done")
    return {
      ...p,
      tokens: [
        { label: "e3a1·77f0·c2…", local: "Mon 09:00" },
        { label: "9b04·1de8·5a…", local: "Wed 13:00" },
        { label: "41c9·b2e3·0f…", local: "Thu 09:00", match: true },
        { label: "d7aa·03be·91…", local: "Fri 15:00" },
      ],
      result: "slots",
    };
  if (name === "ApprovalButton")
    return {
      ...p,
      label: "Approve: reserve the item",
      consequence: "≈ €42 · B and C pay you back · signed with your key",
      ...(state === "disabled"
        ? { disabledReason: "the charter you accepted is out of date" }
        : {}),
    };
  if (name === "CommitmentCard")
    return {
      ...p,
      task:
        state === "pending"
          ? "Reserve the item · ≈ €42"
          : state === "approved"
            ? "Send the resource"
            : state === "suspended"
              ? "Review Friday"
              : "Second delivery",
      assignee: "Member B",
    };
  if (name === "RedactionDiff")
    return {
      ...p,
      original: "Task starts at four from the private location, contact me on +351 …",
      delivered: "Task starts at four",
      verdict: {
        action: "redact",
        policy_id: "no-contact-before-consent",
        paths: ["payload.text[22:]"],
      },
    };
  return tableData(name, p);
}
function tableData(name: string, p: Props): Props {
  if (name === "WhatOthersKnow")
    return {
      ...p,
      rows: [
        {
          participant: "Member B",
          knows: "you're free Thu 09:00; your offer of Resource 1",
          notKnows: "your other slots, your budget",
          because: "task:t3 · PSI",
        },
        {
          participant: "Member C",
          knows: '"your cost is within the plan"',
          notKnows: "the amount",
          because: "vault answer #39",
        },
        {
          participant: "Observer D",
          knows: "results of t1 and t3",
          notKnows: "raw resource log",
          because: "charter rule 2",
        },
        {
          participant: "Host",
          knows: "every message you sent, signed",
          notKnows: "your vault",
          because: "it keeps the log",
        },
      ],
    };
  if (name === "DurableConsent")
    return {
      ...p,
      grants: [
        {
          grantee: "Your agent",
          action: "answer yes/no from your limits",
          scope: "this coalition",
          expires: "it dissolves",
          signed: true,
        },
        {
          grantee: "Planner",
          action: "run PSI on your calendar",
          scope: "tasks t3, t5",
          expires: "Fri 18:00",
          signed: true,
        },
        {
          grantee: "Planner",
          action: "transcribe calls you join",
          scope: "this coalition",
          expires: "each call asks",
          signed: true,
        },
      ],
      requests: [
        {
          id: "r1",
          grantee: "Member B",
          action: "message you on WhatsApp",
          scope: '"needs you" only',
        },
      ],
    };
  return decisionData(name, p);
}
function decisionData(name: string, p: Props): Props {
  if (name === "DecisionLog")
    return {
      ...p,
      entries: [
        {
          time: "11:42",
          participant: "Member A",
          subject: "Plan A",
          revision: bound(2),
          answer: "yes",
          reason: '"Monday matters more than €66"',
          seq: bound(52),
          verified: true,
        },
        {
          time: "11:50",
          participant: "Member B",
          subject: "Plan A",
          revision: bound(2),
          answer: "yes",
          reason: "no reason given",
          seq: bound(53),
          verified: true,
        },
        {
          time: "12:03",
          participant: "Member C",
          subject: "Plan A",
          revision: bound(2),
          answer: "yes",
          reason: "Plan B superseded",
          seq: bound(54),
          verified: true,
        },
        {
          time: "12:03",
          participant: "Host",
          subject: "Host: Plan A decided; stage → Act",
          seq: bound(55),
          verified: true,
        },
      ],
    };
  return p;
}
