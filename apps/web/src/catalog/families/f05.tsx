// SPDX-License-Identifier: Apache-2.0
import { createComponentImplementation, type ReactComponentImplementation } from "@a2ui/react/v0_9";
import { CommonSchemas } from "@a2ui/web_core/v0_9";
import { z } from "zod";
import * as Views from "../../components/f05/views";
import { WireValue } from "../../components/f05/wire";
import { emit } from "../implementations";
import { Bound } from "../schemas";

const binding = CommonSchemas.DataBinding;
const literal = <T extends z.ZodTypeAny>(schema: T) => z.union([schema, binding]);
export const apis = {
  ActsForGraph: {
    name: "ActsForGraph",
    schema: z.object({
      acting: literal(z.string()).optional(),
      agents: literal(z.array(WireValue).max(200)).optional(),
      people: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  AgentPresence: {
    name: "AgentPresence",
    schema: z.object({
      agent: literal(z.string()).optional(),
      latencyMs: literal(Bound).optional(),
      pinnedKid: literal(z.string()).optional(),
      state: literal(z.enum(["live", "idle", "offline"])).optional(),
    }),
  },
  CharterCard: {
    name: "CharterCard",
    schema: z.object({
      revision: literal(Bound).optional(),
      roles: literal(z.array(WireValue).max(200)).optional(),
      rules: literal(z.array(WireValue).max(200)).optional(),
      signedBy: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  CoalitionHeader: {
    name: "CoalitionHeader",
    schema: z.object({
      budget: literal(z.record(WireValue)).optional(),
      counts: literal(z.record(WireValue)).optional(),
      goal: literal(z.string()).optional(),
      pack: literal(z.string()).optional(),
      revision: literal(Bound).optional(),
      title: literal(z.string()),
      yourState: literal(
        z.enum(["agreed", "needs-you", "changed", "private", "blocked"]),
      ).optional(),
    }),
  },
  InviteList: {
    name: "InviteList",
    schema: z.object({
      invitations: literal(z.array(WireValue).max(200)).optional(),
      openSeats: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  LeaveControl: {
    name: "LeaveControl",
    schema: z.object({
      consequences: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  PackChip: {
    name: "PackChip",
    schema: z.object({
      pack: literal(z.record(WireValue)).optional(),
    }),
  },
  ParticipantCard: {
    name: "ParticipantCard",
    schema: z.object({
      act: literal(z.string()).optional(),
      capabilities: literal(z.array(WireValue).max(200)).optional(),
      participant: literal(z.string()).optional(),
      roles: literal(z.array(WireValue).max(200)).optional(),
      seat: literal(Bound).optional(),
      state: literal(z.enum(["agreed", "acting", "owes", "watcher", "invited", "left"])).optional(),
    }),
  },
  RoleChip: {
    name: "RoleChip",
    schema: z.object({
      open: literal(z.boolean()).optional(),
      role: literal(z.string()).optional(),
    }),
  },
  RoleMatrix: {
    name: "RoleMatrix",
    schema: z.object({
      rights: literal(z.array(WireValue).max(200)).optional(),
      roles: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  Roster: {
    name: "Roster",
    schema: z.object({
      members: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  SeatRing: {
    name: "SeatRing",
    schema: z.object({
      goal: literal(z.string()).optional(),
      openSeats: literal(Bound).optional(),
      seats: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  StageTrack: {
    name: "StageTrack",
    schema: z.object({
      current: binding.optional(),
      progress: literal(Bound).optional(),
      stages: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  VendorBadge: {
    name: "VendorBadge",
    schema: z.object({
      framework: literal(z.string()).optional(),
      transport: literal(z.string()).optional(),
    }),
  },
};
export const implementations: ReactComponentImplementation[] = [
  createComponentImplementation(apis.ActsForGraph, ({ props, context }) => (
    <Views.ActsForGraph p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.AgentPresence, ({ props, context }) => (
    <Views.AgentPresence p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.CharterCard, ({ props, context }) => (
    <Views.CharterCard p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.CoalitionHeader, ({ props, context }) => (
    <Views.CoalitionHeader p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.InviteList, ({ props, context }) => (
    <Views.InviteList p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.LeaveControl, ({ props, context }) => (
    <Views.LeaveControl p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.PackChip, ({ props, context }) => (
    <Views.PackChip p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.ParticipantCard, ({ props, context }) => (
    <Views.ParticipantCard p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.RoleChip, ({ props, context }) => (
    <Views.RoleChip p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.RoleMatrix, ({ props, context }) => (
    <Views.RoleMatrix p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.Roster, ({ props, context }) => (
    <Views.Roster p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.SeatRing, ({ props, context }) => (
    <Views.SeatRing p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.StageTrack, ({ props, context }) => (
    <Views.StageTrack p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.VendorBadge, ({ props, context }) => (
    <Views.VendorBadge p={props} send={(name, data) => emit(context, name, data)} />
  )),
];
