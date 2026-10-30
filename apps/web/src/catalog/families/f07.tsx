// SPDX-License-Identifier: Apache-2.0
import { createComponentImplementation, type ReactComponentImplementation } from "@a2ui/react/v0_9";
import { CommonSchemas } from "@a2ui/web_core/v0_9";
import { z } from "zod";
import { WireValue } from "../../components/f05/wire";
import * as Views from "../../components/f07/views";
import { emit } from "../implementations";
import { Bound } from "../schemas";

const binding = CommonSchemas.DataBinding;
const literal = <T extends z.ZodTypeAny>(schema: T) => z.union([schema, binding]);
export const apis = {
  AgendaList: {
    name: "AgendaList",
    schema: z.object({
      day: literal(z.string()).optional(),
      items: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  ArrivalCard: {
    name: "ArrivalCard",
    schema: z.object({
      arrivedAt: literal(z.string()).optional(),
      next: literal(z.string()).optional(),
      others: literal(z.array(WireValue).max(200)).optional(),
      place: literal(z.string()).optional(),
    }),
  },
  CalendarWeek: {
    name: "CalendarWeek",
    schema: z.object({
      events: literal(z.array(WireValue).max(200)).optional(),
      range: literal(z.record(WireValue)).optional(),
    }),
  },
  IndoorMap: {
    name: "IndoorMap",
    schema: z.object({
      liveLayers: literal(z.array(WireValue).max(200)).optional(),
      path: literal(z.array(WireValue).max(200)).optional(),
      plan: literal(z.string()).optional(),
      rooms: literal(z.array(WireValue).max(200)).optional(),
      you: literal(z.record(WireValue)).optional(),
    }),
  },
  LocationShare: {
    name: "LocationShare",
    schema: z.object({
      audience: literal(z.union([z.string(), z.record(WireValue)])).optional(),
      precision: literal(z.enum(["exact", "approximate", "place-only", "off"])).optional(),
      until: literal(z.enum(["task end", "time", "arrival"])).optional(),
    }),
  },
  MapView: {
    name: "MapView",
    schema: z.object({
      areas: literal(z.array(WireValue).max(200)).optional(),
      points: literal(z.array(WireValue).max(200)).optional(),
      routes: literal(z.array(WireValue).max(200)).optional(),
      selected: literal(z.string()).optional(),
      you: literal(z.record(WireValue)).optional(),
    }),
  },
  PlacePicker: {
    name: "PlacePicker",
    schema: z.object({
      pin: literal(z.record(WireValue)).optional(),
      query: literal(z.string()).optional(),
      results: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  RouteCard: {
    name: "RouteCard",
    schema: z.object({
      distance: literal(Bound).optional(),
      costPerMember: literal(Bound).optional(),
      currency: literal(z.string()).optional(),
      eta: literal(z.string()).optional(),
      mode: literal(z.string()).optional(),
      participants: literal(z.array(WireValue).max(200)).optional(),
      progress: literal(Bound).optional(),
      steps: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  TimeZoneStrip: {
    name: "TimeZoneStrip",
    schema: z.object({
      now: literal(z.string()).optional(),
      people: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
};
export const implementations: ReactComponentImplementation[] = [
  createComponentImplementation(apis.AgendaList, ({ props, context }) => (
    <Views.AgendaList p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.ArrivalCard, ({ props, context }) => (
    <Views.ArrivalCard p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.CalendarWeek, ({ props, context }) => (
    <Views.CalendarWeek p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.IndoorMap, ({ props, context }) => (
    <Views.IndoorMap p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.LocationShare, ({ props, context }) => (
    <Views.LocationShare p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.MapView, ({ props, context }) => (
    <Views.MapView p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.PlacePicker, ({ props, context }) => (
    <Views.PlacePicker p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.RouteCard, ({ props, context }) => (
    <Views.RouteCard p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.TimeZoneStrip, ({ props, context }) => (
    <Views.TimeZoneStrip p={props} send={(name, data) => emit(context, name, data)} />
  )),
];
