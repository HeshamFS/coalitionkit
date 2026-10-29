// SPDX-License-Identifier: Apache-2.0
import {
  Banner,
  EmptyState,
  ErrorState,
  Skeleton,
  Toast,
  ToastStack,
} from "../components/feedback";
import {
  Avatar,
  AvatarStack,
  Badge,
  type BadgeKind,
  Button,
  Card,
  Column,
  Grid,
  Heading,
  Panel,
  Row,
  ScopeBadge,
  Tag,
  type TagKind,
  Text,
} from "../components/primitives";
import { Cell, Family, State } from "./Cell";
import { m1, m2, m3, m4, m5 } from "./fixtures";

const TAGS: TagKind[] = ["agreed", "needs", "changed", "private", "blocked"];
const BADGES: [BadgeKind, string][] = [
  ["measured", "Measured"],
  ["signed", "Signed"],
  ["vault", "Vault answer"],
  ["model", "Model output"],
  ["estimate", "Estimate"],
  ["example", "example"],
];

export function Basic() {
  return (
    <>
      <Family n="01a" title="Text and layout">
        <Cell
          name="Text"
          doors={["wide", "compact", "lens", "message", "voice"]}
          props="text: path | literal · variant: body | caption · tone: default | muted | blue · provenance?: id"
        >
          <Text text="Body text, default" />
          <Text text="Body text, muted" tone="muted" />
          <Text text="Body text, blue" tone="blue" />
          <Text text="Caption, default" variant="caption" />
          <Text text="Caption, muted" variant="caption" tone="muted" />
        </Cell>
        <Cell
          name="Heading"
          doors={["wide", "compact", "lens", "message", "voice"]}
          props="text: path | literal · variant: h1 | h2 | h3 · tone: default | blue"
        >
          <Heading text="Heading one" variant="h1" />
          <Heading text="Heading two" variant="h2" />
          <Heading text="Heading three" variant="h3" />
          <Heading text="Heading blue" variant="h2" tone="blue" />
        </Cell>
        <Cell
          name="Row"
          doors={["wide", "compact", "lens", "message", "voice"]}
          props="children: id[] · gap: 4 | 8 | 12 | 16 · align: start | center | end"
        >
          <Row gap={4}>
            <Tag kind="agreed" />
            <Tag kind="needs" />
          </Row>
          <Row gap={16} align="start">
            <Badge label="Gap 16" />
            <Badge label="Wraps on compact" kind="signed" />
          </Row>
        </Cell>
        <Cell
          name="Column"
          doors={["wide", "compact", "lens", "message", "voice"]}
          props="children: id[] · gap: 4 | 8 | 12 | 16"
        >
          <Column gap={4}>
            <Text text="Gap 4, first" />
            <Text text="Gap 4, second" />
          </Column>
          <Column gap={16}>
            <Text text="Gap 16, first" />
            <Text text="Gap 16, second" />
          </Column>
        </Cell>
        <Cell
          name="Grid"
          doors={["wide", "compact", "lens", "message", "voice"]}
          span={2}
          props="children: id[] · columns: 1..4 · gap: 4 | 8 | 12 | 16 · one column on compact"
        >
          <Grid columns={3} gap={8}>
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <Card key={n}>
                <span className="h-title">Cell {n}</span>
              </Card>
            ))}
          </Grid>
          <Grid columns={2} gap={8} compact>
            <Card>
              <span className="h-title">Compact: one column</span>
            </Card>
            <Card>
              <span className="h-title">Second row</span>
            </Card>
          </Grid>
        </Cell>
      </Family>

      <Family n="01b" title="Containers">
        <Cell
          name="Card"
          doors={["wide", "compact", "lens"]}
          span={2}
          props="children: id[] · title?: string · tone: default | live | ask | dashed · scope?: Scope"
          events="open(subject)"
        >
          <div className="g2" style={{ gap: 8 }}>
            <State label="default">
              <Card title="Card 1" scope="coalition">
                <span className="small">Body text</span>
              </Card>
            </State>
            <State label="live">
              <Card title="Card 2" tone="live">
                <span className="small">Changed just now</span>
              </Card>
            </State>
            <State label="ask">
              <Card title="Card 3" tone="ask">
                <span className="small">Needs your answer</span>
              </Card>
            </State>
            <State label="dashed">
              <Card title="Card 4" tone="dashed">
                <span className="small">Placeholder</span>
              </Card>
            </State>
          </div>
        </Cell>
        <Cell
          name="Panel"
          doors={["wide", "compact", "lens"]}
          span={2}
          props="children: id[] · title?: string · scope?: Scope"
        >
          <Panel title="Panel 1" count={3} scope="self">
            <div className="g2" style={{ gap: 6 }}>
              <Card>
                <span className="h-title">Item 1</span>
                <Tag kind="agreed" />
              </Card>
              <Card>
                <span className="h-title">Item 2</span>
                <Tag kind="needs" />
              </Card>
              <Card>
                <span className="h-title">Item 3</span>
                <Tag kind="private" />
              </Card>
              <Card tone="dashed">
                <span className="small">+ Add</span>
              </Card>
            </div>
          </Panel>
        </Cell>
      </Family>

      <Family n="01c" title="Button">
        <Cell
          name="Button · variants"
          doors={["wide", "compact", "lens", "message", "voice"]}
          props="label · variant: primary | secondary | ink | ghost (+ soft, danger, danger-fill on the sheet) · size: sm | md | lg · action: {name, context}"
          events="action.name(context)"
        >
          <Row>
            <Button label="Primary" variant="primary" />
            <Button label="Secondary" />
          </Row>
          <Row>
            <Button label="Ink" variant="ink" />
            <Button label="Soft" variant="soft" />
          </Row>
          <Row>
            <Button label="Ghost" variant="ghost" />
            <Button label="Danger" variant="danger" />
            <Button label="Danger fill" variant="danger-fill" />
          </Row>
        </Cell>
        <Cell
          name="Button · states"
          props="default · hover · pressed · focus · busy (aria-busy) · disabled"
          events="action.name(context)"
        >
          <div className="g3" style={{ gap: 8 }}>
            <State label="default">
              <Button label="Accept" variant="primary" />
            </State>
            <State label="hover">
              <Button label="Accept" variant="primary" forceState="hover" />
            </State>
            <State label="pressed">
              <Button label="Accept" variant="primary" forceState="press" />
            </State>
            <State label="focus">
              <Button label="Accept" variant="primary" forceState="focus" />
            </State>
            <State label="busy">
              <Button label="Sending" variant="primary" busy />
            </State>
            <State label="disabled">
              <Button label="Accept" variant="primary" disabled />
            </State>
          </div>
          <Row>
            <Button label="Accept" disabled />
            <span className="small">Waiting for 2 deciders before this unlocks</span>
          </Row>
        </Cell>
        <Cell
          name="Button · sizes"
          props="sm 28 px · md 32 px · lg 44 px (compact targets are 44 px)"
        >
          <Row>
            <Button label="Small" size="sm" variant="primary" />
            <Button label="Medium" variant="primary" />
            <Button label="Large" size="lg" variant="primary" />
          </Row>
        </Cell>
      </Family>

      <Family n="01d" title="Tag, Badge, ScopeBadge">
        <Cell
          name="Tag"
          doors={["wide", "compact", "lens", "message", "voice"]}
          props="label?: string · kind: agreed | needs | changed | private | blocked (the five words)"
        >
          {TAGS.map((k) => (
            <State key={k} label={k}>
              <Tag kind={k} />
            </State>
          ))}
        </Cell>
        <Cell
          name="Badge"
          doors={["wide", "compact", "lens", "message", "voice"]}
          props="label: string · kind: measured | vault | signed | model | estimate | example"
        >
          <Row>
            {BADGES.map(([k, l]) => (
              <Badge key={k} kind={k} label={l} />
            ))}
          </Row>
        </Cell>
        <Cell
          name="ScopeBadge"
          doors={["wide", "compact", "message"]}
          props="audience: host | self | task:x | role:y | coalition | public · redact: [path]"
        >
          <Column gap={8}>
            {["host", "self", "task:t3", "role:member", "coalition", "public"].map((a) => (
              <Row key={a}>
                <ScopeBadge audience={a} />
              </Row>
            ))}
            <Row>
              <ScopeBadge audience="coalition" redact={["payload.cost"]} />
              <span className="small">with a redaction</span>
            </Row>
          </Column>
        </Cell>
      </Family>

      <Family n="01e" title="Avatar and AvatarStack">
        <Cell
          name="Avatar"
          doors={["wide", "compact", "lens", "message"]}
          span={2}
          props="seat: 1-5 | host | steward · label · presence: live | away | off · ring · size: xs | sm | lg | xl"
        >
          <Row>
            <Avatar seat={1} label="Member 1" size="xs" />
            <Avatar seat={2} label="Member 2" />
            <Avatar seat={3} label="Member 3" size="lg" />
            <Avatar seat={4} label="Member 4" size="xl" />
            <Avatar seat={5} label="Member 5" size="lg" />
            <Avatar seat="host" label="Host" size="lg" />
            <Avatar seat="steward" label="Steward" size="lg" />
          </Row>
          <Row gap={12}>
            <State label="live">
              <Avatar seat={1} label="Member 1" size="lg" presence="live" />
            </State>
            <State label="away">
              <Avatar seat={2} label="Member 2" size="lg" presence="away" />
            </State>
            <State label="off">
              <Avatar seat={3} label="Member 3" size="lg" presence="off" />
            </State>
            <State label="ring">
              <Avatar seat={4} label="Member 4" size="lg" ring />
            </State>
            <State label="speaking">
              <Avatar seat={5} label="Member 5" size="lg" speaking />
            </State>
          </Row>
        </Cell>
        <Cell
          name="AvatarStack"
          doors={["wide", "compact"]}
          span={2}
          props="people: [participant] · max: int"
        >
          <Row>
            <AvatarStack people={[m1, m2, m3, m4, m5]} max={3} />
            <span className="small">5 agents are reading</span>
          </Row>
          <Row>
            <AvatarStack people={[m1, m2]} max={3} />
            <span className="small">2, nothing hidden</span>
          </Row>
        </Cell>
      </Family>

      <Family n="01f" title="Feedback: Banner, Toast, EmptyState, ErrorState, Skeleton">
        <Cell
          name="Banner"
          doors={["wide", "compact", "message"]}
          span={2}
          props="tone: info | ask | blocked | agreed · title · body · action? · dismissible"
          events="banner.action · banner.dismiss"
        >
          <Banner
            tone="info"
            title="The charter changed."
            body="Read revision 3 before you accept anything new."
            action="Read"
          />
          <Banner
            tone="ask"
            title="Two plans tie."
            body="The organizer breaks the tie by the deadline."
          />
          <Banner
            tone="blocked"
            title="The steward blocked a message"
            body="that named a private field. Nothing was sent."
          />
          <Banner
            tone="agreed"
            title="Everyone agreed."
            body="The plan is signed."
            onDismiss={() => {}}
          />
        </Cell>
        <Cell
          name="Toast"
          doors={["wide", "compact", "lens"]}
          span={2}
          props="tone: done | change | error · text ≤ 60 · action? · undoWindow: s"
          events="toast.action · toast.undo"
        >
          <ToastStack>
            {[
              <Toast key="a" tone="done" text="You joined the group" undoWindow={9} />,
              <Toast key="b" tone="change" text="Member 2 changed the date" action="Show" />,
              <Toast key="c" tone="error" text="Could not send. You are offline." action="Retry" />,
            ]}
          </ToastStack>
          <span className="st">
            shown (done with undo window, change, error) · stacked, newest on top · dismissed: gone
          </span>
        </Cell>
        <Cell
          name="EmptyState"
          doors={["wide", "compact"]}
          props="glyph · title · body: who fills it · action?"
          events="action.invoke"
        >
          <EmptyState
            title="No offers yet"
            body="When someone can help with a need, it shows up here. Your agent is listening."
            action="Add what you can offer"
          />
        </Cell>
        <Cell
          name="ErrorState"
          doors={["wide", "compact"]}
          span={2}
          props="state: error | reconnecting · cause · lastSeen · retry · details {code, ref} · missed"
          events="error.retry"
        >
          <ErrorState
            cause="Cannot reach your agent"
            lastSeen="21:58"
            details={{ code: "stream_error", ref: "r-1" }}
          />
          <ErrorState state="reconnecting" cause="" missed={3} />
        </Cell>
        <Cell
          name="Skeleton"
          doors={["wide", "compact"]}
          span={2}
          props="shape: line | block | avatar | card · lines · reserves: px · state: skeleton | filled | live | rest | changed · previous? · provenance?"
        >
          <div className="g2" style={{ gap: 8 }}>
            <State label="skeleton · card">
              <Skeleton shape="card" />
            </State>
            <State label="skeleton · line, avatar, block">
              <Skeleton shape="line" />
              <Skeleton shape="avatar" />
              <Skeleton shape="block" reserves={40} />
            </State>
            <State label="filled">
              <Skeleton state="filled" value="Value 1" reserves={20} />
            </State>
            <State label="live">
              <Skeleton state="live" value="Value 2" reserves={20} />
            </State>
            <State label="rest">
              <Skeleton state="rest" value="Value 3" reserves={20} />
            </State>
            <State label="changed">
              <Skeleton state="changed" value="Value 5" previous="Value 4" reserves={20} />
            </State>
          </div>
        </Cell>
      </Family>
    </>
  );
}
