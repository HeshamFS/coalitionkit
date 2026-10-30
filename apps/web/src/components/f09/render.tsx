// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { Card, type Props, type Send, sendFor, text } from "../f08/shared";
import { ActivityStream } from "./ActivityStream";
import { CanvasPresence } from "./CanvasPresence";
import { ChainView } from "./ChainView";
import { ChangedValue } from "./ChangedValue";
import { ConnectionStatus } from "./ConnectionStatus";
import { ErrorNotice } from "./ErrorNotice";
import { EventRow } from "./EventRow";
import { EvidenceCard } from "./EvidenceCard";
import { GardenerThinking } from "./GardenerThinking";
import { LiveDocks } from "./LiveDocks";
import { LogStream } from "./LogStream";
import { MediaWithMasks } from "./MediaWithMasks";
import { ProvenanceTag } from "./ProvenanceTag";
import { ReceiptBadge } from "./ReceiptBadge";
import { RippleBanner } from "./RippleBanner";
import { StepProgress } from "./StepProgress";
import { StewardVerdict } from "./StewardVerdict";
import { VerifyPanel } from "./VerifyPanel";
import "../../styles/f09.css";

const components: Record<string, (props: { p: Props; send: Send }) => React.ReactNode> = {
  ChangedValue,
  RippleBanner,
  ActivityStream,
  LogStream,
  GardenerThinking,
  CanvasPresence,
  ConnectionStatus,
  LiveDocks,
  StepProgress,
  EventRow,
  ChainView,
  ReceiptBadge,
  ProvenanceTag,
  StewardVerdict,
  EvidenceCard,
  MediaWithMasks,
  VerifyPanel,
  ErrorNotice,
};
export function render(name: string, p: Props, context: ComponentContext) {
  const Component = components[name];
  return (
    <div className="f09">
      <Card name={name} state={text(p.status ?? p.state ?? p.feed ?? p.health)}>
        {Component && <Component p={p} send={sendFor(context)} />}
      </Card>
    </div>
  );
}
