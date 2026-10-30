// SPDX-License-Identifier: Apache-2.0
import { createComponentImplementation } from "@a2ui/react/v0_9";
import { CommonSchemas } from "@a2ui/web_core/v0_9";
import { z } from "zod";
import { dispatch } from "../../components/f02/dispatch";
import * as Views from "../../components/f04/views";
import { Bound } from "../schemas";
export const apis = {
  AcceptanceForm: {
    name: "AcceptanceForm",
    schema: z.object({
      charter: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      consequence: z.union([z.string(), CommonSchemas.DataBinding]),
      decision_deadline: z
        .union([z.string().datetime({ offset: true }), CommonSchemas.DataBinding])
        .optional(),
      diff: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      subject: z.union([
        z.object({ kind: z.string(), id: z.string(), revision: Bound }).strict(),
        CommonSchemas.DataBinding,
      ]),
    }),
  },
  AvailabilityGrid: {
    name: "AvailabilityGrid",
    schema: z.object({
      days: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      slots: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      source: z.union([z.enum(["manual", "calendar"]), CommonSchemas.DataBinding]).optional(),
    }),
  },
  ConsentSeal: {
    name: "ConsentSeal",
    schema: z.object({
      decision_deadline: z
        .union([z.string().datetime({ offset: true }), CommonSchemas.DataBinding])
        .optional(),
      holdMs: z.union([Bound, CommonSchemas.DataBinding]).optional(),
      subject: z.union([
        z.object({ kind: z.string(), id: z.string(), revision: Bound }).strict(),
        CommonSchemas.DataBinding,
      ]),
      summary: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  DocumentShare: {
    name: "DocumentShare",
    schema: z.object({
      preview: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
      document: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      masks: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      purpose: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  FeedbackForm: {
    name: "FeedbackForm",
    schema: z.object({
      audience: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      questions: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  Form: {
    name: "Form",
    schema: z.object({
      description: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      scope: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      submit_label: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      presentation: z.union([z.enum(["fields", "voice"]), CommonSchemas.DataBinding]).optional(),
      conversation: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      show_schema: z.union([z.boolean(), CommonSchemas.DataBinding]).optional(),
      fields: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      submit_event: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      title: z.union([z.string(), CommonSchemas.DataBinding]),
    }),
  },
  LimitField: {
    name: "LimitField",
    schema: z.object({
      shared_values: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
      limits: z
        .union([
          z.array(
            z
              .object({
                id: z.union([z.string(), CommonSchemas.DataBinding]),
                label: z.union([z.string(), CommonSchemas.DataBinding]),
                disclose: z.union([z.enum(["answer-only", "shared"]), CommonSchemas.DataBinding]),
              })
              .strict(),
          ),
          CommonSchemas.DataBinding,
        ])
        .optional(),
      queries: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  NeedForm: {
    name: "NeedForm",
    schema: z.object({
      audience: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      constraints: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      quantity: z.union([Bound, CommonSchemas.DataBinding]).optional(),
      text: z.union([z.string(), CommonSchemas.DataBinding]),
    }),
  },
  OfferForm: {
    name: "OfferForm",
    schema: z.object({
      target_label: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      scope: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      conditions: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      cost: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
      expires: z
        .union([z.string().datetime({ offset: true }), CommonSchemas.DataBinding])
        .optional(),
      target: z.union([z.enum(["need", "task"]), CommonSchemas.DataBinding]).optional(),
      what: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
    }),
  },
  OwnerSign: {
    name: "OwnerSign",
    schema: z.object({
      answer_label: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      subject_label: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      device_label: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      answer: z.union([z.enum(["bool", "choice"]), CommonSchemas.DataBinding]).optional(),
      decision_deadline: z
        .union([z.string().datetime({ offset: true }), CommonSchemas.DataBinding])
        .optional(),
      kid: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      method: z.union([z.enum(["passkey", "hosted key"]), CommonSchemas.DataBinding]).optional(),
      subject: z.union([
        z.object({ kind: z.string(), id: z.string(), revision: Bound }).strict(),
        CommonSchemas.DataBinding,
      ]),
    }),
  },
  Receipt: {
    name: "Receipt",
    schema: z.object({
      decision_deadline: z
        .union([z.string().datetime({ offset: true }), CommonSchemas.DataBinding])
        .optional(),
      hash: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      receipt: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
      remaining: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
      seq: z.union([Bound, CommonSchemas.DataBinding]).optional(),
      subject: z.union([
        z.object({ kind: z.string(), id: z.string(), revision: Bound }).strict(),
        CommonSchemas.DataBinding,
      ]),
    }),
  },
  ReviewStep: {
    name: "ReviewStep",
    schema: z.object({
      notice: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      precheck: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
      sections: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  ValidationSummary: {
    name: "ValidationSummary",
    schema: z.object({
      errors: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
  Wizard: {
    name: "Wizard",
    schema: z.object({
      canSkip: z.union([z.boolean(), CommonSchemas.DataBinding]).optional(),
      current: z.union([z.string(), CommonSchemas.DataBinding]).optional(),
      draft: z.union([z.record(z.unknown()), CommonSchemas.DataBinding]).optional(),
      steps: z.union([z.array(z.unknown()), CommonSchemas.DataBinding]).optional(),
    }),
  },
};
export const implementations = [
  createComponentImplementation(apis.AcceptanceForm, ({ props, context, buildChild }) => (
    <Views.AcceptanceForm
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.AvailabilityGrid, ({ props, context, buildChild }) => (
    <Views.AvailabilityGrid
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.ConsentSeal, ({ props, context, buildChild }) => (
    <Views.ConsentSeal
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.DocumentShare, ({ props, context, buildChild }) => (
    <Views.DocumentShare
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.FeedbackForm, ({ props, context, buildChild }) => (
    <Views.FeedbackForm
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.Form, ({ props, context, buildChild }) => (
    <Views.Form p={props} send={(name, data) => dispatch(context, name, data)} build={buildChild} />
  )),
  createComponentImplementation(apis.LimitField, ({ props, context, buildChild }) => (
    <Views.LimitField
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.NeedForm, ({ props, context, buildChild }) => (
    <Views.NeedForm
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.OfferForm, ({ props, context, buildChild }) => (
    <Views.OfferForm
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.OwnerSign, ({ props, context, buildChild }) => (
    <Views.OwnerSign
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.Receipt, ({ props, context, buildChild }) => (
    <Views.Receipt
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.ReviewStep, ({ props, context, buildChild }) => (
    <Views.ReviewStep
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.ValidationSummary, ({ props, context, buildChild }) => (
    <Views.ValidationSummary
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
  createComponentImplementation(apis.Wizard, ({ props, context, buildChild }) => (
    <Views.Wizard
      p={props}
      send={(name, data) => dispatch(context, name, data)}
      build={buildChild}
    />
  )),
];
