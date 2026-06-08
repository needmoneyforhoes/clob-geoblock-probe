# clob-geoblock-probe

Probes Polymarket CLOB endpoints to find which ones return `403` from a geoblocked region, without placing an order.

Polymarket geoblocks trading endpoints by region, and the block surfaces inconsistently across SDK methods and the raw HTTP routes behind the CDN. This finds the fastest `403` endpoint so the bot can use it as a startup preflight check.

## Scripts

- `geoblock_test.py`: authenticates a wallet once, then fires read, cancel, and raw HTTP probes against the CLOB, tagging each by HTTP status (`200`/`403`/`404`/`400`/`500`/error) and latency.

## Phases

- SDK READ: `get_open_orders`, `get_trades`, `get_last_trades_prices`, `get_order_book`, `get_last_trade_price`, `is_order_scoring`, `are_orders_scoring` (dummy token).
- SDK CANCEL: `cancel_all`, `cancel_orders([])`, `cancel_market_orders(dummy)`. No-ops that still hit the gateway.
- RAW HTTP: direct `httpx` calls bypassing the SDK: `POST /order` (empty body), `GET /tick-size`, `POST /orders` (empty batch), `GET /rewards`, `GET /auth/derive-api-key`, `GET /trade-notifications`.

The summary buckets results into PASS / BLOCKED / ERROR and prints `BEST FOR STARTUP CHECK`: the fastest `403` endpoint, for use as the bot preflight signal. All payloads are empty or dummy, so no order is submitted.

## Requirements

- Python 3.9+, `httpx`.
- `py_clob_client_v2`, the vendored Polymarket CLOB SDK. Raw L2 HMAC headers come from `py_clob_client_v2.headers.headers.create_level_2_headers`. Edit upstream, not here.

## Usage

```bash
export PRIVATE_KEY=$(grep "^PRIVATE_KEY" .arbVenv | cut -d= -f2)
python3 geoblock_test.py
```

Loads `PRIVATE_KEY` from `.arbVenv` to derive CLOB API creds; never committed (`.arbVenv`, `.env*`, `*.key`, `*.pem` are git-ignored). The wallet only signs auth headers; no order is placed, so there is no fill risk.
