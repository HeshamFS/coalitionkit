// SPDX-License-Identifier: Apache-2.0
import { Cell, Family, State } from "../Cell";
import { One } from "../Drawn";
import "../../styles/f07.css";
import { examples } from "../../components/f07/examples";

export { examples };
export function Sheet07() {
  return (
    <div className="sheet" data-testid="sheet-07">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 07 · example data</div>
          <div className="sheet-title">Places and time</div>
        </div>
      </div>
      <Family n="07a" title="Places, routes and sharing">
        <Cell
          name="MapView"
          props={"areas \u00b7 points \u00b7 routes \u00b7 selected \u00b7 you"}
          events={"map.select(point) \u00b7 map.area(polygon)"}
          span={2}
        >
          {examples.MapView?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="MapView" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="IndoorMap"
          props={"liveLayers \u00b7 path \u00b7 plan \u00b7 rooms \u00b7 you"}
          events={"map.select(room)"}
        >
          {examples.IndoorMap?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="IndoorMap" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="RouteCard"
          props={"distance \u00b7 eta \u00b7 mode \u00b7 participants \u00b7 progress \u00b7 steps"}
          events={"display only"}
        >
          {examples.RouteCard?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="RouteCard" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="PlacePicker"
          props={"pin \u00b7 query \u00b7 results"}
          events={"place.pick(ref)"}
          span={2}
        >
          {examples.PlacePicker?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="PlacePicker" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="LocationShare"
          props={"audience \u00b7 precision \u00b7 until"}
          events={"location.share \u00b7 location.stop"}
        >
          {examples.LocationShare?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="LocationShare" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="ArrivalCard"
          props={"arrivedAt \u00b7 next \u00b7 others \u00b7 place"}
          events={"display only"}
        >
          {examples.ArrivalCard?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="ArrivalCard" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
      </Family>
      <Family n="07b" title="Time: calendar, zones and agenda">
        <Cell
          name="CalendarWeek"
          props={"events \u00b7 range"}
          events={"event.open \u00b7 calendar.export"}
          span={2}
        >
          {examples.CalendarWeek?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="CalendarWeek" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell name="TimeZoneStrip" props={"now \u00b7 people"} events={"display only"}>
          {examples.TimeZoneStrip?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="TimeZoneStrip" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell name="AgendaList" props={"day \u00b7 items"} events={"item.action"}>
          {examples.AgendaList?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="AgendaList" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
      </Family>
    </div>
  );
}
