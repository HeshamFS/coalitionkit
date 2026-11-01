# travel-disruption

A Discipline Pack for travellers stranded by a cancelled last flight. An organizer and the travellers agree onward rides and rooms with a car desk and a hotel shuttle. Businesses join as agents over A2A with a signed card.

- **Roles:** traveller, organizer, car desk, shuttle.
- **Words:** task is a ride, resource a seat, need a trip, offer a seat offer.
- **Strategy:** `auction`. A seat offer's cost is its minutes plus its money, with `minute_value: 40`, so arrival time is traded against price. Rides are grouped by destination (one trip per destination).
- **Policies:** `no-contact-before-yes` blocks phone numbers and email addresses in shared text; `spend-needs-person` holds an offer or note that names a price of EUR 500 or more until a person says yes; `mask-booking-reference` redacts booking references (`BK-` and six characters) in notes.
- **Private by design:** a traveller's spending limit and phone are `x-private` and stay in the vault.
- **Connector:** `connectors/car-desk/car_desk.py` is a small, standard-library-only business agent. It joins with a signed card and holds vehicles whose seats it offers. It runs out of process in the kit's connector container.

## Run

```
uv run coalitionkit up --pack packs/travel-disruption
uv run coalitionkit pack validate packs/travel-disruption
uv run coalitionkit pack eval packs/travel-disruption
uv run coalitionkit pack accept packs/travel-disruption
uv run coalitionkit pack connectors packs/travel-disruption --host http://127.0.0.1:8000 --coalition <id> --run
```

The last command needs Docker. `views.yaml` is kept beside the pack but not listed in `pack.yaml`; add `views: views.yaml` to use it on a host that supplies the core catalog.

## What it never does

- Book, pay or contact anyone. It plans; a person signs each booking.
- Accept a yes from an agent as a booking.
- Share contact details or spending limits.
- Name real people, airlines or companies; all places and businesses are invented.
