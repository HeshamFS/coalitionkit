// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { Card, type Props, type Send, sendFor, text } from "../f08/shared";
import { ApprovalButton } from "./ApprovalButton";
import { CanaryMonitor } from "./CanaryMonitor";
import { CommitmentCard } from "./CommitmentCard";
import { ConsentCard } from "./ConsentCard";
import { DecisionLog } from "./DecisionLog";
import { DisclosureLadder } from "./DisclosureLadder";
import { DurableConsent } from "./DurableConsent";
import { OverlapView } from "./OverlapView";
import { PrivateField } from "./PrivateField";
import { ProjectionNote } from "./ProjectionNote";
import { RedactionDiff } from "./RedactionDiff";
import { ScopeBadge } from "./ScopeBadge";
import { StaleNotice } from "./StaleNotice";
import { VaultCard } from "./VaultCard";
import { VoteTally } from "./VoteTally";
import { WhatOthersKnow } from "./WhatOthersKnow";
import "../../styles/f08.css";

const components: Record<string, (props: { p: Props; send: Send }) => React.ReactNode> = {
  ApprovalButton,
  ConsentCard,
  VaultCard,
  DisclosureLadder,
  PrivateField,
  ScopeBadge,
  OverlapView,
  WhatOthersKnow,
  ProjectionNote,
  RedactionDiff,
  CanaryMonitor,
  VoteTally,
  StaleNotice,
  CommitmentCard,
  DurableConsent,
  DecisionLog,
};
export function render(name: string, p: Props, context: ComponentContext) {
  const Component = components[name];
  return (
    <div className="f08">
      <Card name={name} state={text(p.status ?? p.state ?? p.feed ?? p.health)}>
        {Component && <Component p={p} send={sendFor(context)} />}
      </Card>
    </div>
  );
}
