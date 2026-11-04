// SPDX-License-Identifier: Apache-2.0
// Panel labels and geometry as drawn in the component sheet.
export const panels = [
  {
    title: "Forms an agent generates",
    panels: [
      {
        name: "Form",
        title: "Form · from a schema",
        span: 2,
        props:
          "title · fields[] {id, kind: text | number | money | datetime | choice | multi | bool | place | file, label, required, private: no | answer-only | vault, help} · submit_event · the renderer, not the agent, draws every field",
        events: "→ form.submit(values) → typed coalition message · private values → vault",
      },
      {
        name: "ValidationSummary",
        title: "ValidationSummary · errors",
        span: 1,
        props:
          "errors[] {field, text} · links focus the field · validated twice: renderer (shape) and host (schema)",
        events: "",
      },
      {
        name: "Form",
        title: "Form · voice door",
        span: 1,
        props:
          "same Form, asked one field at a time · read-back before submit · private fields go to the vault, never the transcript",
        events: "",
      },
    ],
  },
  {
    title: "Step-by-step flows",
    panels: [
      {
        name: "Wizard",
        title: "Wizard · write the charter",
        span: 2,
        props:
          "steps[] {id, label, fields | components} · current · canSkip · draft autosave (host, organizer only) · agent suggestion beside, never pre-filled",
        events: "",
      },
      {
        name: "NeedForm",
        title: "NeedForm · publish a need",
        span: 1,
        props: "text · constraints[] {kind, value} · quantity · audience · → coalition.need",
        events: "",
      },
      {
        name: "OfferForm",
        title: "OfferForm · answer a need",
        span: 1,
        props:
          "target (need | task) · what · cost {amount, kind: quote | estimate} · conditions[] · expires · → coalition.offer",
        events: "",
      },
    ],
  },
  {
    title: "Private input: availability, limits, documents",
    panels: [
      {
        name: "AvailabilityGrid",
        title: "AvailabilityGrid · stays in your vault",
        span: 2,
        props:
          "days[] · slots per day · value: set of free slots (vault) · source: manual | calendar import · output: PSI tokens only",
        events: "",
      },
      {
        name: "LimitField",
        title: "LimitField · answer-only",
        span: 1,
        props:
          "limits[] {id, label, value (vault), disclose: answer-only | shared} · queries[] {question, answer, asker, time}",
        events: "",
      },
      {
        name: "DocumentShare",
        title: "DocumentShare · redact first",
        span: 1,
        props:
          "document (vault) · masks[] {region | field, by: agent | person} · purpose · share → Evidence with masks applied host-side",
        events: "",
      },
    ],
  },
  {
    title: "Acceptance: the moments that end in a signature",
    panels: [
      {
        name: "AcceptanceForm",
        title: "AcceptanceForm · charter revision",
        span: 1,
        props:
          "charter · revision · diff[] {rule, before, after} · consequence of not accepting · acknowledgement required · → owner-signed decide(charter)",
        events: "",
      },
      {
        name: "ConsentSeal",
        title: "ConsentSeal · press and hold",
        span: 1,
        props:
          "subject · revision · summary · hold 1.2 s (keyboard: hold Space; screen reader: confirm dialog) · → owner-signed decide or commit",
        events: "",
      },
      {
        name: "OwnerSign",
        title: "OwnerSign · confirm the key",
        span: 1,
        props:
          "subject · answer · key id · device method: passkey | hosted key (MCP) · result: signed decide (C-18)",
        events: "",
      },
      {
        name: "Receipt",
        title: "Receipt · after signing",
        span: 1,
        props:
          "seq · receipt (host-signed) · hash · remaining deciders · change allowed until deadline (a new decide supersedes)",
        events: "",
      },
      {
        name: "ReviewStep",
        title: "ReviewStep · before submit",
        span: 2,
        props:
          "sections[] {label, summary, editStep} · irreversibility notice · steward pre-check result · submit",
        events: "",
      },
      {
        name: "FeedbackForm",
        title: "FeedbackForm · after dissolve",
        span: 2,
        props:
          "questions[] {kind: choice | scale | text} · audience: me | coalition | pack authors (opt-in) · feeds Memory",
        events: "",
      },
    ],
  },
];
