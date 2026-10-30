// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import type { ComponentProps } from "react";
import type { IconName } from "../../ui/Icon";
import { Calendar } from "./Calendar";
import { DataDisplay, Gauge, Rich, Slots, Time } from "./Data";
import { Filter } from "./Filter";
import { Choices, Field, Search, Toggle } from "./Forms";
import { Banner, EmptyState, ErrorState, Skeleton, Toast } from "./feedback";
import { Glyph as Icon } from "./Glyph";
import { FileDrop, Media } from "./Media";
import { Menu, Overlay, Split, Tooltip } from "./Overlays";
import * as P from "./primitives";
import { Slider } from "./Slider";
import { Children, dispatch, number, obj, type Props, rows, str, type ViewProps } from "./shared";
import "../../styles/f01.css";
import "./details.css";
import "./choice.css";
import "./calendar.css";
import "./round4.css";
import "./media.css";
import "./round5.css";

export function Foundation({
  name,
  p,
  context,
  build,
}: {
  name: string;
  p: Props;
  context: ComponentContext;
  build: ViewProps["build"];
}) {
  const send = (event: string, data?: Props) => dispatch(context, event, data);
  const prefix = `f01-${encodeURIComponent(context.dataContext.surface?.id ?? "surface")}-`;
  const args = {
    name,
    p: {
      ...p,
      id: context.componentModel.id,
      ...(name === "Tooltip" ? { target: `${prefix}${encodeURIComponent(str(p.target))}` } : {}),
      ...(name === "Popover" && p.anchor
        ? { anchor: `${prefix}${encodeURIComponent(str(p.anchor))}` }
        : {}),
    },
    send,
    build,
  };
  return (
    <div
      id={`${prefix}${encodeURIComponent(context.componentModel.id)}`}
      className={`f01 f01-root-${name}`}
      data-component={name}
    >
      <Content {...args} />
    </div>
  );
}

function Content(args: ViewProps) {
  return primitive(args) ?? adornment(args) ?? feedback(args) ?? interactive(args);
}

function primitive(args: ViewProps) {
  const { name, p, send, build } = args;
  const declared = obj(p.action);
  const action = typeof declared.name === "string" ? declared : obj(declared.event);
  const invoke = () => {
    if (typeof action.name === "string") send(action.name, obj(action.context));
  };
  const kids = <Children value={p.children} build={build} />;
  switch (name) {
    case "Text":
      return (
        <>
          <P.Text
            text={str(p.text)}
            variant={p.variant as "body" | "caption"}
            tone={p.tone as "default" | "muted" | "blue"}
          />
          {p.provenance ? (
            <P.Badge kind={p.provenance as P.BadgeKind} label={str(p.provenance)} />
          ) : null}
        </>
      );
    case "Heading":
      return (
        <P.Heading
          text={str(p.text)}
          variant={p.variant as "h1" | "h2" | "h3"}
          tone={p.tone as "default" | "blue"}
        />
      );
    case "Button":
      return (
        <P.Button
          label={str(p.label)}
          variant={(p.tone ?? p.variant) as P.ButtonVariant}
          icon={p.icon ? <Icon name={str(p.icon)} /> : undefined}
          trailingIcon={p.trailingIcon ? <Icon name={str(p.trailingIcon)} /> : undefined}
          size={p.size as "sm" | "md" | "lg"}
          disabled={!!p.disabled}
          busy={!!p.busy}
          onClick={invoke}
        />
      );
    case "Icon":
      return (
        <span
          role="img"
          aria-label={str(p.label) || "Icon"}
          style={{ color: p.tone === "blue" ? "var(--blue)" : undefined }}
        >
          <Icon
            name={str(p.name) as IconName}
            size={p.size === "24" ? "lg" : p.size === "16" ? "sm" : undefined}
          />
        </span>
      );
    case "IconButton":
      return (
        <button
          type="button"
          className="icon-btn"
          aria-label={str(p.ariaLabel)}
          title={str(p.ariaLabel)}
          onClick={invoke}
        >
          <Icon name={str(p.icon, "plus") as IconName} />
        </button>
      );
    case "ButtonGroup":
      return <div className="f01-button-group">{kids}</div>;
    case "Row":
      return (
        <P.Row
          gap={Number(p.gap ?? 8) as 4 | 8 | 12 | 16}
          align={p.align as "start" | "center" | "end"}
        >
          {kids}
        </P.Row>
      );
    case "Column":
      return <P.Column gap={Math.max(0, number(p.spacing, Number(p.gap ?? 8)))}>{kids}</P.Column>;
    case "Grid":
      return (
        <div
          className="f01-grid"
          style={{
            gridTemplateColumns: `repeat(${Math.max(1, Math.min(4, number(p.columns, 2)))}, minmax(0,1fr))`,
            gap: Number(p.gap ?? 12),
          }}
        >
          {kids}
          <Fields p={p} />
        </div>
      );
    case "Card":
      return (
        <P.Card
          title={str(p.title)}
          tone={p.tone as ComponentProps<typeof P.Card>["tone"]}
          scope={str(p.scope) || undefined}
          onOpen={() => send("open", { subject: { id: str(p.id), kind: "card" } })}
        >
          <Fields p={p} />
          {kids}
        </P.Card>
      );
    case "Panel":
      return (
        <P.Panel title={str(p.title)} scope={str(p.scope) || undefined}>
          <Fields p={p} />
          {kids}
        </P.Panel>
      );
    default:
      return null;
  }
}
function adornment(args: ViewProps) {
  const { name, p } = args;
  switch (name) {
    case "Tag":
      return <P.Tag kind={(p.kind as P.TagKind) ?? "agreed"} label={str(p.label)} />;
    case "Badge":
      return <P.Badge kind={p.kind as P.BadgeKind} label={str(p.label)} />;
    case "Avatar":
      return (
        <P.Avatar
          label={str(p.label)}
          seat={seat(p.seat)}
          presence={p.presence as "live" | "away" | "off"}
          ring={!!p.ring}
          size={p.size as "xs" | "sm" | "lg" | "xl"}
        />
      );
    case "AvatarStack":
      return (
        <P.AvatarStack
          people={rows(p.people).map((person) => ({
            seat: seat(person.seat),
            label: str(person.label),
          }))}
          max={number(p.max, 3)}
        />
      );
    default:
      return null;
  }
}
function feedback(args: ViewProps) {
  const { name, p, send } = args;
  const action = obj(p.action);
  switch (name) {
    case "Banner":
      return (
        <Banner
          title={str(p.title)}
          body={str(p.body)}
          tone={(p.tone as ComponentProps<typeof Banner>["tone"]) ?? "info"}
          action={str(action.label) || undefined}
          onAction={() => send("banner.action")}
          onDismiss={action.dismissible === true ? () => send("banner.dismiss") : undefined}
        />
      );
    case "Toast":
      return (
        <Toast
          text={str(p.text)}
          tone={(p.tone as ComponentProps<typeof Toast>["tone"]) ?? "done"}
          action={str(action.label) || undefined}
          undoWindow={number(p.undoWindow)}
          onAction={() => send("toast.action")}
          onUndo={() => send("toast.undo")}
        />
      );
    case "EmptyState":
      return (
        <EmptyState
          title={str(p.title)}
          body={str(p.body)}
          glyph={str(p.glyph, "inbox") as IconName}
          action={str(action.label) || undefined}
          onAction={() => send("action.invoke")}
        />
      );
    case "ErrorState":
      return (
        <>
          <ErrorState
            cause={str(p.cause)}
            retry={p.retry !== false}
            lastSeen={str(p.lastSeen)}
            details={
              p.details
                ? { code: str(obj(p.details).code), ref: str(obj(p.details).ref) }
                : undefined
            }
            onRetry={() => send("error.retry")}
          />
          {p.missedEvents !== undefined && (
            <div className="f01-reconnecting" role="status">
              <span className="spinner" />
              Reconnecting · <b>{number(p.missedEvents)} missed events</b> will replay
            </div>
          )}
        </>
      );
    case "Skeleton":
      return (
        <Skeleton
          shape={p.shape as ComponentProps<typeof Skeleton>["shape"]}
          state={p.state as ComponentProps<typeof Skeleton>["state"]}
          lines={number(p.lines, 2)}
          reserves={p.reserves ? number(p.reserves) : undefined}
          previous={str(p.previous)}
          provenance={p.provenance as P.BadgeKind}
        />
      );
    case "Spinner":
      return (
        <span role="status" aria-label={str(p.label, "Loading")} className="row small">
          <span className="spinner" aria-hidden="true" />
          {p.label ? str(p.label) : null}
        </span>
      );
    case "Divider":
      return p.label ? (
        <div className="row">
          <hr className="f01-divider" />
          <span className="st f01-divider-label">{str(p.label)}</span>
          <hr className="f01-divider" />
        </div>
      ) : (
        <hr className="f01-divider" />
      );
    case "Chip":
      return (
        <button
          type="button"
          className={`chip ${p.selected ? "chip-on" : ""}`}
          disabled={!!p.disabled}
          style={p.dashed ? { borderStyle: "dashed" } : undefined}
          aria-pressed={!!p.selected}
          onClick={() => send("select", { id: p.id })}
        >
          {p.seat ? <span className={`pin s${str(p.seat)}`} /> : null}
          {str(p.label)}
        </button>
      );
    case "Link":
      return (
        <a
          href={/^https:\/\//.test(str(p.href)) ? str(p.href) : "#"}
          onClick={(e) => {
            e.preventDefault();
            send("link.open", { href: p.href });
          }}
        >
          {str(p.text)}
        </a>
      );
    case "RichText":
      return <Rich {...args} />;
    default:
      return null;
  }
}
function interactive(args: ViewProps) {
  const { name } = args;
  switch (name) {
    case "TextField":
    case "TextArea":
    case "NumberField":
      return <Field {...args} />;
    case "DateTimeInput":
      return args.p.range ? <Calendar {...args} /> : <Field {...args} />;
    case "Slider":
      return <Slider {...args} />;
    case "CheckBox":
    case "Switch":
      return <Toggle {...args} />;
    case "ChoicePicker":
    case "RadioGroup":
    case "SegmentedControl":
    case "Tabs":
      return <Choices {...args} />;
    case "SearchField":
    case "CommandPalette":
      return <Search {...args} />;
    case "FilterBar":
      return <Filter {...args} />;
    case "Modal":
    case "Sheet":
    case "Drawer":
    case "Popover":
      return <Overlay {...args} />;
    case "Menu":
      return <Menu {...args} />;
    case "SplitButton":
      return <Split {...args} />;
    case "Tooltip":
      return <Tooltip {...args} />;
    case "Table":
    case "List":
    case "KeyValue":
      return <DataDisplay {...args} />;
    case "Progress":
    case "Meter":
      return <Gauge {...args} />;
    case "SlotPicker":
      return <Slots {...args} />;
    case "TimeZone":
    case "Deadline":
      return <Time {...args} />;
    case "Image":
    case "Video":
    case "AudioPlayer":
      return <Media {...args} />;
    case "FileDrop":
      return <FileDrop {...args} />;
    default:
      return null;
  }
}
const seat = (v: unknown): P.Seat =>
  v === "host" || v === "steward" ? v : (Math.max(1, Math.min(5, Number(v) || 1)) as P.Seat);
function Fields({ p }: { p: Props }) {
  return (
    <>
      {rows(p.fields).length > 0 && (
        <DataDisplay name="KeyValue" p={{ pairs: p.fields }} send={() => {}} build={() => null} />
      )}
      {p.status ? (
        <P.Tag kind={p.status === "needs-you" ? "needs" : (p.status as P.TagKind)} />
      ) : null}
      {p.provenance ? (
        <P.Badge label={str(p.provenance)} kind={p.provenance as P.BadgeKind} />
      ) : null}
    </>
  );
}
