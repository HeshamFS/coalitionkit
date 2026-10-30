// SPDX-License-Identifier: Apache-2.0
import { createComponentImplementation } from "@a2ui/react/v0_9";
import { CommonSchemas, markChildRef } from "@a2ui/web_core/v0_9";
import { z } from "zod";
import { dispatch } from "../../components/f02/dispatch";
import * as Views from "../../components/f02/views";
import { Bound } from "../schemas";
export const apis = {
  AccountMenu: {
    name: "AccountMenu",
    schema: z.object({
      agents: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      appearance: z
        .union([z.enum(["light", "dark", "system"]), CommonSchemas.DataBinding])
        .optional(),
      channels: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      identity: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  AgentDock: {
    name: "AgentDock",
    schema: z.object({
      agent: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      composer: z.union([z.enum(["text", "voice"]), CommonSchemas.DataBinding]).optional(),
      messages: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  BoardTemplate: {
    name: "BoardTemplate",
    schema: z.object({
      cards: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      columns: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  ConsentTray: {
    name: "ConsentTray",
    schema: z.object({
      requests: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  Deck: {
    name: "Deck",
    schema: z.object({
      sections: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      selected: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  EntryComposer: {
    name: "EntryComposer",
    schema: z.object({
      attachments: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      goal: z.union([z.enum(["text", "voice"]), CommonSchemas.DataBinding]).optional(),
      packs: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  InviteCard: {
    name: "InviteCard",
    schema: z.object({
      channels: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      expires: z
        .union([z.string().datetime({ offset: true }), CommonSchemas.DataBinding])
        .optional(),
      invitation: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
      role: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  JoinScreen: {
    name: "JoinScreen",
    schema: z.object({
      charter: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
      inviter: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      subject: z.union([
        z.object({ kind: z.string(), id: z.string(), revision: Bound }).strict(),
        CommonSchemas.DataBinding,
      ]),
    }),
  },
  LensCard: {
    name: "LensCard",
    schema: z.object({
      body: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      eyebrow: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      gestures: z.union([Bound, CommonSchemas.DataBinding]).optional(),
      title: z.union([z.string(), CommonSchemas.DataBinding]),
    }),
  },
  MessageDoor: {
    name: "MessageDoor",
    schema: z.object({
      choices: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      receipt: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      text: z.union([z.string(), CommonSchemas.DataBinding]),
    }),
  },
  NotificationCenter: {
    name: "NotificationCenter",
    schema: z.object({
      items: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  PageHeader: {
    name: "PageHeader",
    schema: z.object({
      actions: z.union([Bound, CommonSchemas.DataBinding]).optional(),
      crumbs: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      eyebrow: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      tabs: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      title: z.union([z.string(), CommonSchemas.DataBinding]),
    }),
  },
  PhoneShell: {
    name: "PhoneShell",
    schema: z.object({
      header: markChildRef(
        z.union([z.string(), CommonSchemas.DataBinding]),
        "component-id",
      ).optional(),
      stack: markChildRef(
        z.union([CommonSchemas.ChildList, CommonSchemas.DataBinding]),
        "child-list",
      ).optional(),
      tabs: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  RoomShell: {
    name: "RoomShell",
    schema: z.object({
      canvas: markChildRef(
        z.union([z.string(), CommonSchemas.DataBinding]),
        "component-id",
      ).optional(),
      coalition: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      deck: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      dock: markChildRef(
        z.union([z.string(), CommonSchemas.DataBinding]),
        "component-id",
      ).optional(),
      presence: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      stage: z.union([CommonSchemas.DataBinding, z.never()]).optional(),
      tray: markChildRef(
        z.union([z.string(), CommonSchemas.DataBinding]),
        "component-id",
      ).optional(),
    }),
  },
  SplitView: {
    name: "SplitView",
    schema: z.object({
      detail: markChildRef(
        z.union([CommonSchemas.ChildList, CommonSchemas.DataBinding]),
        "child-list",
      ).optional(),
      items: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      selected: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  StageBar: {
    name: "StageBar",
    schema: z.object({
      current: z.union([CommonSchemas.DataBinding, z.never()]).optional(),
      stages: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  TopBar: {
    name: "TopBar",
    schema: z.object({
      actions: z.union([Bound, CommonSchemas.DataBinding]).optional(),
      presence: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      stage: z.union([CommonSchemas.DataBinding, z.never()]).optional(),
      title: z.union([z.string(), CommonSchemas.DataBinding]),
    }),
  },
  VoiceTurn: {
    name: "VoiceTurn",
    schema: z.object({
      choices: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      confirm: z.union([z.boolean(), CommonSchemas.DataBinding]).optional(),
      earcon: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      script: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  WiringDrawer: {
    name: "WiringDrawer",
    schema: z.object({
      event_ref: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      projection: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
};
export const implementations = [
  createComponentImplementation(apis.AccountMenu, ({ props, context, buildChild }) => (
    <Views.AccountMenu
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.AgentDock, ({ props, context, buildChild }) => (
    <Views.AgentDock
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.BoardTemplate, ({ props, context, buildChild }) => (
    <Views.BoardTemplate
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.ConsentTray, ({ props, context, buildChild }) => (
    <Views.ConsentTray
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.Deck, ({ props, context, buildChild }) => (
    <Views.Deck p={props} send={(name, data) => dispatch(context, name, data)} build={buildChild} />
  )),
  createComponentImplementation(apis.EntryComposer, ({ props, context, buildChild }) => (
    <Views.EntryComposer
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.InviteCard, ({ props, context, buildChild }) => (
    <Views.InviteCard
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.JoinScreen, ({ props, context, buildChild }) => (
    <Views.JoinScreen
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.LensCard, ({ props, context, buildChild }) => (
    <Views.LensCard
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.MessageDoor, ({ props, context, buildChild }) => (
    <Views.MessageDoor
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.NotificationCenter, ({ props, context, buildChild }) => (
    <Views.NotificationCenter
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.PageHeader, ({ props, context, buildChild }) => (
    <Views.PageHeader
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.PhoneShell, ({ props, context, buildChild }) => (
    <Views.PhoneShell
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.RoomShell, ({ props, context, buildChild }) => (
    <Views.RoomShell
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.SplitView, ({ props, context, buildChild }) => (
    <Views.SplitView
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.StageBar, ({ props, context, buildChild }) => (
    <Views.StageBar
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.TopBar, ({ props, context, buildChild }) => (
    <Views.TopBar
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.VoiceTurn, ({ props, context, buildChild }) => (
    <Views.VoiceTurn
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.WiringDrawer, ({ props, context, buildChild }) => (
    <Views.WiringDrawer
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
];
