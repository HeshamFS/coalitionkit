// SPDX-License-Identifier: Apache-2.0
import { createComponentImplementation } from "@a2ui/react/v0_9";
import { CommonSchemas, markChildRef } from "@a2ui/web_core/v0_9";
import { z } from "zod";
import { dispatch } from "../../components/f02/dispatch";
import * as Views from "../../components/f03/views";
import { Bound } from "../schemas";
export const apis = {
  AgentHandoff: {
    name: "AgentHandoff",
    schema: z.object({
      choices: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      question: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      reason: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      rule: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  AgentStatus: {
    name: "AgentStatus",
    schema: z.object({
      budget: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
      state: z
        .union([
          z.enum(["listening", "answering", "needs-you", "paused", "offline"]),
          CommonSchemas.DataBinding,
        ])
        .optional(),
      task: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  AskAgent: {
    name: "AskAgent",
    schema: z.object({
      kind: z
        .union([z.enum(["bool", "number-range", "choice"]), CommonSchemas.DataBinding])
        .optional(),
      task_id: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      text: z.union([z.string(), CommonSchemas.DataBinding]),
      to: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  CallInvite: {
    name: "CallInvite",
    schema: z.object({
      caller: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      consents: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      listeners: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      title: z.union([z.string(), CommonSchemas.DataBinding]),
    }),
  },
  CallSummary: {
    name: "CallSummary",
    schema: z.object({
      decided: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      duration: z.union([Bound, CommonSchemas.DataBinding]).optional(),
      needs: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      offers: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      questions: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  ChannelDigest: {
    name: "ChannelDigest",
    schema: z.object({
      channel: z.union([z.enum(["email", "sms"]), CommonSchemas.DataBinding]).optional(),
      items: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      period: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  CoalitionThread: {
    name: "CoalitionThread",
    schema: z.object({
      messages: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      typing: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  Composer: {
    name: "Composer",
    schema: z.object({
      attachments: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      audience: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      commands: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      mentions: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  DiarizedTranscript: {
    name: "DiarizedTranscript",
    schema: z.object({
      extracted: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      segments: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  ElicitationForm: {
    name: "ElicitationForm",
    schema: z.object({
      binding: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
      decision_deadline: z
        .union([z.string().datetime({ offset: true }), CommonSchemas.DataBinding])
        .optional(),
      message: z.union([z.string(), CommonSchemas.DataBinding]),
      schema: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
      subject: z.union([
        z.object({ kind: z.string(), id: z.string(), revision: Bound }).strict(),
        CommonSchemas.DataBinding,
      ]),
    }),
  },
  McpAppView: {
    name: "McpAppView",
    schema: z.object({
      resourceUri: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      tree: markChildRef(
        z.union([CommonSchemas.ChildList, CommonSchemas.DataBinding]),
        "child-list",
      ).optional(),
    }),
  },
  Message: {
    name: "Message",
    schema: z.object({
      policy: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      redactions: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      state: z
        .union([
          z.enum(["sending", "delivered", "seen", "failed", "redacted", "blocked"]),
          CommonSchemas.DataBinding,
        ])
        .optional(),
      text: z.union([z.string(), CommonSchemas.DataBinding]),
    }),
  },
  NegotiationTheatre: {
    name: "NegotiationTheatre",
    schema: z.object({
      events: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      speakers: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  ToolCall: {
    name: "ToolCall",
    schema: z.object({
      args: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
      state: z.union([z.enum(["running", "done", "failed"]), CommonSchemas.DataBinding]).optional(),
      summary: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      tool: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  VideoCall: {
    name: "VideoCall",
    schema: z.object({
      captions: z.union([z.boolean(), CommonSchemas.DataBinding]).optional(),
      recording: z.union([z.enum(["transcript", "off"]), CommonSchemas.DataBinding]).optional(),
      tiles: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  VoiceCall: {
    name: "VoiceCall",
    schema: z.object({
      caption: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      participants: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      speaking: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
};
export const implementations = [
  createComponentImplementation(apis.AgentHandoff, ({ props, context, buildChild }) => (
    <Views.AgentHandoff
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.AgentStatus, ({ props, context, buildChild }) => (
    <Views.AgentStatus
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.AskAgent, ({ props, context, buildChild }) => (
    <Views.AskAgent
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.CallInvite, ({ props, context, buildChild }) => (
    <Views.CallInvite
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.CallSummary, ({ props, context, buildChild }) => (
    <Views.CallSummary
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.ChannelDigest, ({ props, context, buildChild }) => (
    <Views.ChannelDigest
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.CoalitionThread, ({ props, context, buildChild }) => (
    <Views.CoalitionThread
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.Composer, ({ props, context, buildChild }) => (
    <Views.Composer
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.DiarizedTranscript, ({ props, context, buildChild }) => (
    <Views.DiarizedTranscript
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.ElicitationForm, ({ props, context, buildChild }) => (
    <Views.ElicitationForm
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.McpAppView, ({ props, context, buildChild }) => (
    <Views.McpAppView
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.Message, ({ props, context, buildChild }) => (
    <Views.Message
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.NegotiationTheatre, ({ props, context, buildChild }) => (
    <Views.NegotiationTheatre
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.ToolCall, ({ props, context, buildChild }) => (
    <Views.ToolCall
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.VideoCall, ({ props, context, buildChild }) => (
    <Views.VideoCall
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.VoiceCall, ({ props, context, buildChild }) => (
    <Views.VoiceCall
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
];
