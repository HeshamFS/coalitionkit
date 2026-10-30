// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { Card, type Props, type Send, sendFor, text } from "../f08/shared";
import { ChannelHandoff } from "./ChannelHandoff";
import { ChannelSettings } from "./ChannelSettings";
import { CoalitionArchive } from "./CoalitionArchive";
import { CostMeter } from "./CostMeter";
import { DissolveSummary } from "./DissolveSummary";
import { DoorMatrix } from "./DoorMatrix";
import { ExportControl } from "./ExportControl";
import { LessonReview } from "./LessonReview";
import { MessageTemplate } from "./MessageTemplate";
import { MetricTile } from "./MetricTile";
import { NotificationCard } from "./NotificationCard";
import { Scorecard } from "./Scorecard";
import { SkillCard } from "./SkillCard";
import "../../styles/f11.css";

const components: Record<string, (props: { p: Props; send: Send }) => React.ReactNode> = {
  DoorMatrix,
  NotificationCard,
  ChannelSettings,
  ChannelHandoff,
  MessageTemplate,
  DissolveSummary,
  CostMeter,
  MetricTile,
  Scorecard,
  ExportControl,
  LessonReview,
  SkillCard,
  CoalitionArchive,
};
export function render(name: string, p: Props, context: ComponentContext) {
  const Component = components[name];
  return (
    <div className="f11">
      <Card name={name} state={text(p.status ?? p.state ?? p.feed ?? p.health)}>
        {Component && <Component p={p} send={sendFor(context)} />}
      </Card>
    </div>
  );
}
