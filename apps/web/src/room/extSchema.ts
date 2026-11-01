// SPDX-License-Identifier: Apache-2.0
// A pack adds fields to needs and offers only inside `ext`, described by a JSON Schema. This reads
// the flat object schema into fields, checks typed values before anything is sent, and keeps the
// values the schema marks private out of the public body.

export type JsonSchema = {
  type?: string;
  title?: string;
  description?: string;
  enum?: unknown[];
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  format?: string;
  properties?: Record<string, JsonSchema>;
  required?: string[];
  "x-private"?: boolean;
};

/** The catalog form kinds the schema form can draw (sheet 04). */
export type ExtKind = "text" | "number" | "choice" | "bool" | "datetime";

export type ExtField = {
  key: string;
  title: string;
  description: string;
  kind: ExtKind;
  options: string[];
  required: boolean;
  /** Held in the owner's vault: never typed here and never put in a public body. */
  private: boolean;
  schema: JsonSchema;
};

export type Values = Record<string, unknown>;

function kindOf(schema: JsonSchema): ExtKind | null {
  if (Array.isArray(schema.enum) && schema.enum.length > 0) return "choice";
  if (schema.type === "boolean") return "bool";
  if (schema.type === "number" || schema.type === "integer") return "number";
  if (schema.type === "string") return schema.format === "date-time" ? "datetime" : "text";
  return null;
}

/** The fields of a flat object schema; properties of other shapes are left out. */
export function fieldsOf(schema: JsonSchema | null | undefined): ExtField[] {
  const properties = schema?.properties ?? {};
  const required = new Set(schema?.required ?? []);
  const fields: ExtField[] = [];
  for (const [key, prop] of Object.entries(properties)) {
    const kind = kindOf(prop);
    if (!kind) continue;
    fields.push({
      key,
      title: prop.title ?? key,
      description: prop.description ?? "",
      kind,
      options: kind === "choice" ? (prop.enum ?? []).map(String) : [],
      required: required.has(key),
      private: prop["x-private"] === true,
      schema: prop,
    });
  }
  return fields;
}

const blank = (v: unknown) => v === undefined || v === null || v === "";

function checkNumber(f: ExtField, raw: unknown): string {
  const n = Number(raw);
  if (!Number.isFinite(n)) return `${f.title} must be a number`;
  if (f.schema.type === "integer" && !Number.isInteger(n)) {
    return `${f.title} must be a whole number`;
  }
  const { minimum, maximum } = f.schema;
  if (minimum !== undefined && n < minimum) return `${f.title} must be at least ${minimum}`;
  if (maximum !== undefined && n > maximum) return `${f.title} must be at most ${maximum}`;
  return "";
}

function checkText(f: ExtField, raw: unknown): string {
  const s = String(raw);
  const { minLength, maxLength, pattern } = f.schema;
  if (minLength !== undefined && s.length < minLength) {
    return `${f.title} must have at least ${minLength} characters`;
  }
  if (maxLength !== undefined && s.length > maxLength) {
    return `${f.title} must have at most ${maxLength} characters`;
  }
  if (pattern !== undefined) {
    try {
      if (!new RegExp(pattern, "u").test(s)) return `${f.title} does not match the expected form`;
    } catch {
      return "";
    }
  }
  return "";
}

/** One message per field that does not fit its schema. Private fields are not checked here. */
export function validate(fields: ExtField[], values: Values): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const f of fields) {
    if (f.private) continue;
    const raw = values[f.key];
    if (f.kind === "bool") {
      if (f.required && raw !== true) errors[f.key] = `${f.title} is required`;
      continue;
    }
    if (blank(raw)) {
      if (f.required) errors[f.key] = `${f.title} is required`;
      continue;
    }
    let message = "";
    if (f.kind === "choice") {
      message = f.options.includes(String(raw)) ? "" : `${f.title} must be one of the choices`;
    } else if (f.kind === "number") {
      message = checkNumber(f, raw);
    } else if (f.kind === "datetime") {
      message = Number.isNaN(Date.parse(String(raw))) ? `${f.title} must be a date and time` : "";
    } else {
      message = checkText(f, raw);
    }
    if (message) errors[f.key] = message;
  }
  return errors;
}

/** The typed `ext` body. A private field never appears in it, and an empty optional one is left out. */
export function toExt(fields: ExtField[], values: Values): Values {
  const ext: Values = {};
  for (const f of fields) {
    if (f.private) continue;
    const raw = values[f.key];
    if (f.kind === "bool") {
      if (raw === true || f.required) ext[f.key] = raw === true;
    } else if (!blank(raw)) {
      if (f.kind === "number") ext[f.key] = Number(raw);
      else if (f.kind === "datetime") ext[f.key] = new Date(String(raw)).toISOString();
      else if (f.kind === "choice") {
        ext[f.key] = (f.schema.enum ?? []).find((o) => String(o) === String(raw)) ?? raw;
      } else ext[f.key] = raw;
    }
  }
  return ext;
}
