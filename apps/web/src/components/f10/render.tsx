// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { Card, type Props, type Send, sendFor, text } from "../f08/shared";
import { AttackTests } from "./AttackTests";
import { CaptureCard } from "./CaptureCard";
import { DeviceAlarm } from "./DeviceAlarm";
import { DeviceReading } from "./DeviceReading";
import { EdgeReaderStatus } from "./EdgeReaderStatus";
import { MintedAgentCard } from "./MintedAgentCard";
import { MintPipeline } from "./MintPipeline";
import { PublishApproval } from "./PublishApproval";
import { ScheduleTwin } from "./ScheduleTwin";
import "../../styles/f10.css";

const components: Record<string, (props: { p: Props; send: Send }) => React.ReactNode> = {
  CaptureCard,
  MintPipeline,
  AttackTests,
  PublishApproval,
  MintedAgentCard,
  EdgeReaderStatus,
  DeviceReading,
  DeviceAlarm,
  ScheduleTwin,
};
export function render(name: string, p: Props, context: ComponentContext) {
  const Component = components[name];
  return (
    <div className="f10">
      <Card name={name} state={text(p.status ?? p.state ?? p.feed ?? p.health)}>
        {Component && <Component p={p} send={sendFor(context)} />}
      </Card>
    </div>
  );
}
