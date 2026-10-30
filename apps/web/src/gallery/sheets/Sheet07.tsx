// SPDX-License-Identifier: Apache-2.0

import { examples } from "../../components/f07/examples";
import { Family } from "../Cell";
import { One } from "../Drawn";
import { Panel } from "./Sheet05";
import "../../styles/f07.css";

export { examples };

function Demo({ name }: { name: string }) {
  return (
    <>
      {examples[name]?.map((e) => (
        <One
          key={`${e.state}-${JSON.stringify(e.props)}`}
          component={name}
          props={e.props}
          data={{ current: "Decide" }}
        />
      ))}
    </>
  );
}
export function Sheet07() {
  return (
    <div className="sheet f07-sheet" data-testid="sheet-07">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">
            coalitionkit/v0_9 · family 07 · example data · maps illustrative
          </div>
          <div className="sheet-title">Places and time</div>
          <div className="sheet-sub">
            Where things happen and when: maps with points, routes and areas, indoor plans, routes
            on the move, places to choose, how precisely you share where you are, and the calendar
            the coalition runs on.
          </div>
        </div>
        <div className="h-right">
          <span className="badge b-example">Example data</span>
          <span className="scope">Map · Timeline · Calendar</span>
        </div>
      </div>
      <Family n="07a" title="Maps">
        <Panel
          name="MapView"
          title="MapView · points, route, areas"
          events="→ map.select(point) · map.area(polygon)"
          summary={
            "points[] {id, label, kind, lat, lng, ref?} \u00b7 routes[] {path, mode, eta} \u00b7 areas[] {polygon, label} \u00b7 you {position, precision} \u00b7 selected \u00b7 tiles from a configured provider; agents never send coordinates of others beyond their shared precision"
          }
          span
        >
          <Demo name="MapView" />
        </Panel>
        <Panel
          name="IndoorMap"
          title="IndoorMap · indoor plan"
          summary={
            "plan (pack or venue asset) \u00b7 rooms[] \u00b7 you \u00b7 path[] \u00b7 liveLayers[] {label, value, source} \u00b7 accessible route option"
          }
        >
          <Demo name="IndoorMap" />
        </Panel>
        <Panel
          name="RouteCard"
          title="RouteCard · on the move"
          summary={
            "mode \u00b7 eta \u00b7 distance \u00b7 progress \u00b7 legs[] {label, state, time} \u00b7 participants[] \u00b7 source of position (task app | member share)"
          }
        >
          <Demo name="RouteCard" />
        </Panel>
        <Panel
          name="PlacePicker"
          title="PlacePicker · search and pin"
          summary={
            "query \u00b7 results[] {place, distance, facts[], limitCheck (vault)} \u00b7 pin \u00b7 source: provider search | offers in this coalition \u00b7 \u2192 field value (place ref)"
          }
          span
        >
          <Demo name="PlacePicker" />
        </Panel>
        <Panel
          name="LocationShare"
          title="LocationShare · precision"
          summary={
            "audience (scope) \u00b7 precision: exact | ~500 m | place-only | off \u00b7 until: task end | time | arrival \u00b7 vault keeps the raw fix"
          }
        >
          <Demo name="LocationShare" />
        </Panel>
        <Panel
          name="ArrivalCard"
          title="ArrivalCard · geofence"
          summary={
            "place \u00b7 arrivedAt \u00b7 next step \u00b7 others' arrival at their shared precision only \u00b7 posts task progress, not position"
          }
        >
          <Demo name="ArrivalCard" />
        </Panel>
      </Family>
      <Family n="07b" title="Time: calendar, zones and agenda">
        <Panel
          name="CalendarWeek"
          title="CalendarWeek · coalition and private busy"
          summary={
            "range \u00b7 events[] {task | deadline | private-busy, start, end, assignee} \u00b7 private busy drawn from your vault, never sent \u00b7 export ics (yours only)"
          }
          span
        >
          <Demo name="CalendarWeek" />
        </Panel>
        <Panel
          name="TimeZoneStrip"
          title="TimeZoneStrip · local times"
          summary={
            "people[] {participant, tz, workingHours (vault: shared as ranges only)} \u00b7 now \u00b7 overlap (PSI) \u00b7 viewer tz first"
          }
        >
          <Demo name="TimeZoneStrip" />
        </Panel>
        <Panel
          name="AgendaList"
          title="AgendaList · today"
          summary={
            "day \u00b7 items[] {time, title, state, action?} \u00b7 voice reads the next two items only"
          }
        >
          <Demo name="AgendaList" />
        </Panel>
      </Family>
    </div>
  );
}
