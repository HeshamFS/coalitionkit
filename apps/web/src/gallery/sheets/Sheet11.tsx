// SPDX-License-Identifier: Apache-2.0
import { PreviewState } from "../../components/f08/shared";
import { examples } from "../../components/f11/examples";
import { Family } from "../Cell";
import { One } from "../Drawn";
import "../../styles/f11.css";

const panels = [
  {
    title: "DoorMatrix · ConsentCard on six doors",
    name: "DoorMatrix",
    span: 4,
    props:
      "component · doors[]: wide | compact | message | voice | lens | mcp-app · per-door rules: targets 44 px (compact), ≤ 1 024 chars (message), ≤ 3 sentences + confirm (voice), ≤ 2 gestures, no money (lens)",
    empty: false,
  },
  {
    title: "NotificationCard · lock screen",
    name: "NotificationCard",
    span: 1,
    props:
      'title (coalition) · body ≤ 90 chars, no private values · deep link · collapse by coalition · only "needs you" and outcomes notify',
    empty: false,
  },
  {
    title: "ChannelSettings · quiet hours",
    name: "ChannelSettings",
    span: 1,
    props:
      "channels[] {kind, level: everything | needs-you | next-step | digest | off} · quiet {from, to, tz} · per-coalition override · durable consent per channel",
    empty: false,
  },
  {
    title: "ChannelHandoff · move to a door that can",
    name: "ChannelHandoff",
    span: 1,
    props:
      "from door · to door · reason (money | identity | too long) · same subject + revision carried over · expires with the request",
    empty: false,
  },
  {
    title: "MessageTemplate · WhatsApp business",
    name: "MessageTemplate",
    span: 1,
    props:
      "template id · params[] (no private fields) · quick replies[] ≤ 3 · 24 h session rule · opt-out",
    empty: false,
  },
  {
    title: "DissolveSummary · what we did",
    name: "DissolveSummary",
    span: 2,
    props:
      "goal · outcome: reached | partly | not | deadline · counts (from log) · contributions[] {participant, tasks, hours} · cost (meter) · sealed log ref · each number bound to its events",
    empty: false,
  },
  {
    title: "CostMeter · by role and model",
    name: "CostMeter",
    span: 1,
    props:
      "total · budget · rows[] {role, model, tokens, cost} · per participant (own only) · warning 80 % · hard stop 100 % · source: meter, never estimates",
    empty: false,
  },
  {
    title: "Scorecard · MetricTile",
    name: "Scorecard",
    span: 1,
    props:
      'tiles[] {label, value, unit, context, source run} · empty state "not run yet" · targets shown as targets, never as results',
    empty: false,
  },
  {
    title: "ExportControl · take it or wipe it",
    name: "ExportControl",
    span: 1,
    props:
      "items[] {kind, size, included} · export → download · wipe → vault only, with confirm · log immutability stated",
    empty: false,
  },
  {
    title: "LessonReview · what your agent should remember",
    name: "LessonReview",
    span: 2,
    props:
      "lessons[] {text, from (event refs), scope: private | shareable, kind} · never stores judgements about people · person approves each · → agent memory (vault)",
    empty: false,
  },
  {
    title: "SkillCard · a reusable pattern",
    name: "SkillCard",
    span: 1,
    props:
      "name · source coalition · charter rules[] · task templates[] · roles[] · shareable as a pack draft (author-signed) · used count",
    empty: false,
  },
  {
    title: "CoalitionArchive · past coalitions",
    name: "CoalitionArchive",
    span: 2,
    props:
      "items[] {coalition, pack, ended, outcome, yourCost, log ref} · read-only · search · delete local copy",
    empty: false,
  },
  {
    title: "EmptyArchive · first time",
    name: "CoalitionArchive",
    span: 2,
    props: "the archive's empty state · same mark as the entry composer, seats empty",
    empty: true,
  },
];
function Panel({ panel }: { panel: (typeof panels)[number] }) {
  const example = examples.find((e) => e.name === panel.name);
  const state = panel.empty ? example?.states.find((s) => s.state === "empty") : example?.states[0];
  return (
    <div className={`cell${panel.span > 1 ? ` span${panel.span}` : ""}`} data-panel={panel.title}>
      <div className="head">
        <span className="cell-name">{panel.title}</span>
        {panel.name === "DissolveSummary" && (
          <span className="h-right badge b-signed">log sealed #88</span>
        )}
        {panel.name === "DoorMatrix" && (
          <span className="h-right badge b-signed">same A2UI node, six renderers</span>
        )}
        {panel.name === "MessageTemplate" && (
          <span className="h-right door">
            <span>message</span>
          </span>
        )}
        {panel.name === "NotificationCard" && (
          <span className="h-right door">
            <span>push</span>
          </span>
        )}
        {panel.name === "Scorecard" && <span className="h-right badge b-measured">acceptance</span>}
        {panel.name === "CostMeter" && <span className="h-right badge b-measured">meter</span>}
        {panel.name === "LessonReview" && (
          <span className="h-right badge b-model">suggested by your agent</span>
        )}
      </div>
      <div className="demo">
        {panel.name === "NotificationCard" ? (
          <div className="f11-lockscreen">
            <div className="f11-lockscreen-clock">
              <div>11:58</div>
              <span>Thursday 5 November</span>
            </div>
            <One
              component="NotificationCard"
              props={{
                title: "Coalition 1",
                body: "Plan A needs your answer by 14:00.",
                link: "/room/1",
              }}
            />
            <One
              component="NotificationCard"
              props={{
                title: "Coalition 2",
                body: "Everyone agreed. The plan is signed.",
                link: "/room/2",
              }}
            />
          </div>
        ) : (
          state && (
            <PreviewState value={state.state}>
              <One
                component={panel.name}
                props={
                  panel.name === "MessageTemplate"
                    ? {
                        ...state.props,
                        quickReplies: { value: 2, event_ref: "example:1" },
                        params: [
                          "Coalition 1",
                          "A decision needs you: Plan A, by 14:00 today.",
                          {
                            replies: [
                              { id: "open", label: "Open" },
                              { id: "remind", label: "Remind me at 13:00" },
                            ],
                          },
                        ],
                      }
                    : state.props
                }
              />
            </PreviewState>
          )
        )}
      </div>
      <div className="props">{panel.props}</div>
    </div>
  );
}
export function Sheet11() {
  return (
    <div className="sheet sheet-11" data-testid="sheet-11">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 11 · example data</div>
          <div className="sheet-title">Channels, ending and memory</div>
          <div className="sheet-sub">
            How one component reaches each door, how people are told without being nagged, and how a
            coalition ends: what it achieved, what it cost, what each person keeps and what their
            agent learns.
          </div>
        </div>
        <div className="h-right">
          <span className="badge b-example">Example data</span>
          <span className="scope">doors · notifications · dissolve · lessons</span>
        </div>
      </div>
      <Family n="11a" title="One component, every door">
        {panels.slice(0, 5).map((panel) => (
          <Panel key={panel.title} panel={panel} />
        ))}
      </Family>
      <Family n="11b" title="Ending: dissolve, results and cost">
        {panels.slice(5, 8).map((panel) => (
          <Panel key={panel.title} panel={panel} />
        ))}
      </Family>
      <Family n="11c" title="What you keep: export, lessons and skills">
        {panels.slice(8, 13).map((panel) => (
          <Panel key={panel.title} panel={panel} />
        ))}
      </Family>
      <details className="family-extra">
        <summary>Additional catalog states</summary>
        {examples.map((example) => (
          <div key={example.name}>
            {example.states
              .slice(
                example.name === "CoalitionArchive" || example.name === "NotificationCard"
                  ? 2
                  : example.name === "MetricTile"
                    ? 0
                    : 1,
              )
              .map((state) => (
                <PreviewState key={state.state} value={state.state}>
                  <One component={example.name} props={state.props} />
                </PreviewState>
              ))}
          </div>
        ))}
      </details>
    </div>
  );
}
