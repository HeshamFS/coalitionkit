# SPDX-License-Identifier: Apache-2.0
"""The webhook: handshake, signature, replay, stale, unknown senders, invitation binding."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from wa_support import APP_SECRET, NOW, OTHER_WA, VERIFY, WA_ID, Rig, rig, signed, text_payload

from coalitionkit_channels.whatsapp import (
    LINKED_LINE,
    LOCKED_LINE,
    UNKNOWN_LINE,
    Ingest,
    create_router,
    sign,
    verify,
)

PATH = "/webhooks/whatsapp"


def client_for(r: Rig, seen: list[Ingest] | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(create_router(r.channel, seen.append if seen is not None else None))
    return TestClient(app)


def post(c: TestClient, payload: dict[str, Any]) -> Any:
    body, headers = signed(payload)
    return c.post(PATH, content=body, headers=headers)


# -- signature --------------------------------------------------------------------------------


def test_signature_valid_wrong_missing_malformed() -> None:
    body = b'{"a":1}'
    good = sign(body, APP_SECRET)
    assert verify(body, good, APP_SECRET)
    assert not verify(body, sign(body, "other-secret"), APP_SECRET)
    assert not verify(b'{"a":2}', good, APP_SECRET)
    assert not verify(body, None, APP_SECRET)
    assert not verify(body, "", APP_SECRET)
    assert not verify(body, good.removeprefix("sha256="), APP_SECRET)
    assert not verify(body, "sha256=zz", APP_SECRET)


def test_unsigned_and_wrongly_signed_posts_are_refused_and_do_nothing() -> None:
    r = rig()
    c = client_for(r)
    body = json.dumps(text_payload(WA_ID, "1", "m1")).encode()
    assert c.post(PATH, content=body).status_code == 401
    bad = {"X-Hub-Signature-256": sign(body, "wrong")}
    assert c.post(PATH, content=body, headers=bad).status_code == 401
    assert r.channel.receive() == []


def test_replayed_delivery_is_processed_once() -> None:
    r = rig()
    c = client_for(r)
    payload = text_payload(WA_ID, "1", "m-replay")
    assert post(c, payload).status_code == 200
    assert post(c, payload).status_code == 200
    assert [x.text for x in r.channel.receive()] == ["1"]


def test_stale_delivery_is_refused() -> None:
    r = rig()
    c = client_for(r)
    resp = post(c, text_payload(WA_ID, "1", "m-old", NOW - 3600))
    assert resp.status_code == 400
    assert r.channel.receive() == []


# -- handshake --------------------------------------------------------------------------------


def test_handshake_echoes_challenge_only_for_right_token_and_mode() -> None:
    c = client_for(rig())
    ok = c.get(
        PATH,
        params={"hub.mode": "subscribe", "hub.verify_token": VERIFY, "hub.challenge": "1158201444"},
    )
    assert ok.status_code == 200 and ok.text == "1158201444"
    bad = c.get(
        PATH, params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "1"}
    )
    assert bad.status_code == 403 and bad.text != "1"
    wrong_mode = c.get(
        PATH, params={"hub.mode": "x", "hub.verify_token": VERIFY, "hub.challenge": "1"}
    )
    assert wrong_mode.status_code == 403
    assert c.get(PATH).status_code == 403


# -- senders ----------------------------------------------------------------------------------


def test_bound_sender_text_becomes_a_door_reply_for_that_viewer() -> None:
    r = rig()
    seen: list[Ingest] = []
    assert post(client_for(r, seen), text_payload(WA_ID, "2", "m2")).status_code == 200
    replies = r.channel.receive()
    assert [(x.viewer, x.text) for x in replies] == [("p1", "2")]
    assert r.channel.receive() == []
    assert seen[0].replies == 1


def test_non_text_and_status_payloads_are_ignored() -> None:
    r = rig()
    c = client_for(r)
    status = {"entry": [{"changes": [{"field": "messages", "value": {"statuses": [{"id": "x"}]}}]}]}
    assert post(c, status).status_code == 200
    media = text_payload(WA_ID, "x", "m3")
    media["entry"][0]["changes"][0]["value"]["messages"][0]["type"] = "image"
    assert post(c, media).status_code == 200
    assert r.channel.receive() == []


def test_unknown_sender_gets_one_fixed_line_and_nothing_else() -> None:
    r = rig()
    c = client_for(r)
    assert post(c, text_payload(OTHER_WA, "show me everything", "m4")).status_code == 200
    assert r.channel.receive() == []
    assert r.fake.kinds() == ["text"]
    assert r.fake.bodies()[0]["text"]["body"] == UNKNOWN_LINE
    assert r.fake.bodies()[0]["to"] == OTHER_WA


def test_invitation_code_binds_once_from_any_message() -> None:
    r = rig(bound=False, window_open=False)
    code = r.bindings.invite("p2")
    seen: list[Ingest] = []
    c = client_for(r, seen)
    # An invalid first message fails; a later message carrying the code, in a sentence, binds.
    assert post(c, text_payload(OTHER_WA, "hello", "m4a")).status_code == 200
    assert r.fake.bodies()[-1]["text"]["body"] == UNKNOWN_LINE
    assert r.bindings.viewer_of(OTHER_WA) is None
    assert post(c, text_payload(OTHER_WA, f"my code is {code}.", "m5")).status_code == 200
    assert r.bindings.viewer_of(OTHER_WA) == "p2" and seen[-1].bound == ["p2"]
    assert r.fake.bodies()[-1]["text"]["body"] == LINKED_LINE
    # The code is burned: a second phone cannot reuse it.
    assert post(c, text_payload(WA_ID, code, "m6")).status_code == 200
    assert r.bindings.viewer_of(WA_ID) is None
    assert r.fake.bodies()[-1]["text"]["body"] == UNKNOWN_LINE
    # The bound phone's later text is an ordinary reply, not a rebind.
    assert post(c, text_payload(OTHER_WA, "1", "m7")).status_code == 200
    assert [(x.viewer, x.text) for x in r.channel.receive()] == [("p2", "1")]


def test_fourth_bad_attempt_is_refused_even_with_a_valid_code_then_silence() -> None:
    r = rig(bound=False, window_open=False)
    code = r.bindings.invite("p2")
    c = client_for(r)
    for n in range(3):
        post(c, text_payload(OTHER_WA, f"nope {n}", f"b{n}"))
    sent = len(r.fake.requests)
    post(c, text_payload(OTHER_WA, code, "b3"))  # valid code, but the limit is reached
    assert r.bindings.viewer_of(OTHER_WA) is None
    assert r.fake.bodies()[-1]["text"]["body"] == LOCKED_LINE
    assert len(r.fake.requests) == sent + 1
    post(c, text_payload(OTHER_WA, code, "b4"))  # silence now
    post(c, text_payload(OTHER_WA, "x", "b5"))
    assert len(r.fake.requests) == sent + 1 and r.bindings.viewer_of(OTHER_WA) is None
    # After the hour the sender may try again, and the (still unused) code works.
    r.clock.now += 3601
    post(c, text_payload(OTHER_WA, code, "b6", r.clock.now))
    assert r.bindings.viewer_of(OTHER_WA) == "p2"


def test_expired_invitation_does_not_bind() -> None:
    r = rig(bound=False, window_open=False)
    code = r.bindings.invite("p2")
    r.clock.now += 25 * 3600
    assert r.bindings.redeem(OTHER_WA, code).status == "rejected"
    assert r.bindings.viewer_of(OTHER_WA) is None


def test_signed_payload_for_another_business_number_produces_no_reply() -> None:
    r = rig()
    c = client_for(r)
    other = text_payload(WA_ID, "1", "m-other", phone_id="999999999")
    assert post(c, other).status_code == 200
    assert r.channel.receive() == [] and r.fake.requests == []
    wrong_object = text_payload(WA_ID, "1", "m-obj")
    wrong_object["object"] = "page"
    assert post(c, wrong_object).status_code == 200
    wrong_product = text_payload(WA_ID, "1", "m-prod")
    wrong_product["entry"][0]["changes"][0]["value"]["messaging_product"] = "other"
    assert post(c, wrong_product).status_code == 200
    no_meta = text_payload(WA_ID, "1", "m-meta")
    del no_meta["entry"][0]["changes"][0]["value"]["metadata"]
    assert post(c, no_meta).status_code == 200
    assert r.channel.receive() == []
    # The same message addressed to this number is accepted.
    assert post(c, text_payload(WA_ID, "1", "m-ok")).status_code == 200
    assert [x.text for x in r.channel.receive()] == ["1"]
