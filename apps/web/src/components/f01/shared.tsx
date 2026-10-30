// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { Fragment, type ReactNode } from "react";
export type Props = Record<string, unknown>;
export type ViewProps = {
  name: string;
  p: Props;
  send: (name: string, data?: Props) => void;
  build: (id: string, basePath?: string) => ReactNode;
};
export const str = (v: unknown, fallback = ""): string => (typeof v === "string" ? v : fallback);
export const obj = (v: unknown): Props =>
  v && typeof v === "object" && !Array.isArray(v) ? (v as Props) : {};
export const rows = (v: unknown): Props[] => (Array.isArray(v) ? v.map(obj) : []);
export const number = (v: unknown, fallback = 0): number =>
  typeof v === "number"
    ? v
    : typeof obj(v).value === "number"
      ? (obj(v).value as number)
      : fallback;
export const shown = (v: unknown): string =>
  typeof v === "string"
    ? v
    : typeof v === "number"
      ? String(v)
      : typeof v === "boolean"
        ? String(v)
        : typeof obj(v).value === "number"
          ? String(obj(v).value)
          : "";
export function Children({ value, build }: { value: unknown; build: ViewProps["build"] }) {
  return (
    <>
      {(Array.isArray(value) ? value : []).map((child) => {
        const id = typeof child === "string" ? child : str(obj(child).id);
        return <Fragment key={id}>{build(id, str(obj(child).basePath) || undefined)}</Fragment>;
      })}
    </>
  );
}
export function dispatch(context: ComponentContext, name: string, data: Props = {}) {
  void context.dispatchAction({ event: { name, context: data } });
}
