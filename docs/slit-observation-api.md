# Slit observation API

`GET /api/slit-observations?limit=250` returns persisted shared slit observations for the current inspection session, newest footage first.

Successful `POST /api/evidence/capture-auto` responses for `slit-two-lane` sessions now also include `observation_id`, linking the response to the historical shared-frame ledger.

The existing `records` and `diagnostics` response fields remain present. Single-belt capture behavior is unchanged.
