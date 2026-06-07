# clob-geoblock-probe

A lightweight geoblock / CDN reachability probe for the **Polymarket CLOB**. It exercises every CLOB endpoint with authenticated requests and reports which ones return `403` (geoblocked) — without ever placing or risking an order.

## Why it exists

Polymarket geoblocks trading endpoints by region, and the block surfaces inconsistently across the SDK methods and the raw HTTP routes behind the CDN. The trading bot needs a *cheap, fast* preflight check it can run at startup to detect a block before it tries to trade. This probe scans all candidate endpoints and identifies the lightest one (fastest `403`) to wire into the bot's preflight.

## How it works

`geoblock_test.py` authenticates a real wallet once, then fires a sequence of low/zero-risk calls and tags each by HTTP status (`200` / `403` / `404` / `400` / `500` / error) with its latency:

| Phase | What it probes |
| --- | --- |
| SDK READ | `get_open_orders`, `get_trades`, `get_last_trades_prices`, `get_order_book`, `get_last_trade_price`, `is_order_scoring`, `are_orders_scoring` (dummy token) |
| SDK CANCEL | `cancel_all`, `cancel_orders([])`, `cancel_market_orders(dummy)` — no-ops that still hit the gateway |
| RAW HTTP | Direct `httpx` calls bypassing the SDK: `POST /order` (empty body), `GET /tick-size`, `POST /orders` (empty batch), `GET /rewards`, `GET /auth/derive-api-key`, `GET /trade-notifications` |

The summary buckets results into PASS / BLOCKED / ERROR and prints **`BEST FOR STARTUP CHECK`** — the fastest `403` endpoint — to use as the bot's preflight geoblock signal. No order is ever submitted (empty/dummy payloads only).

## Requirements

- Python 3.9+
- `httpx`
- `py_clob_client_v2` — the Polymarket CLOB SDK (vendored from the engine; raw L2 HMAC headers come from `py_clob_client_v2.headers.headers.create_level_2_headers`). Edit upstream, not here.
- **A funded-wallet private key.** The script needs `PRIVATE_KEY` to derive CLOB API creds. The key lives in `.arbVenv` and is loaded into the environment at runtime — it is **never** committed (`.arbVenv`, `.env*`, `*.key`, `*.pem` are git-ignored).

## Usage

```bash
export PRIVATE_KEY=$(grep "^PRIVATE_KEY" .arbVenv | cut -d= -f2)
python3 geoblock_test.py
```

Read-only / no-op only: the wallet signs auth headers but no order is placed, so there is no fill risk.

---

> Private research software. No warranty; trades/handles real funds at your own risk.
