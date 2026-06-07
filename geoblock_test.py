#!/usr/bin/env python3
"""
Geoblock endpoint scanner — tests ALL CLOB endpoints to find the lightest
one that triggers 403 without needing real orders.

Usage: export PRIVATE_KEY=$(grep "^PRIVATE_KEY" .arbVenv | cut -d= -f2) && python3 geoblock_test.py
"""
import os, sys, json, time
import httpx

PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
CLOB_HOST   = "https://clob.polymarket.com"
CHAIN_ID    = 137

if not PRIVATE_KEY:
    print("❌ Set PRIVATE_KEY env var first")
    sys.exit(1)

# ── 1. Init CLOB client for auth headers ───────────────────────────
from py_clob_client_v2.client import ClobClient
clob = ClobClient(host=CLOB_HOST, key=PRIVATE_KEY, chain_id=CHAIN_ID)
try:
    creds = clob.create_or_derive_api_key()
    clob.set_api_creds(creds)
    print(f"✅ Auth OK\n")
except Exception as e:
    print(f"❌ Auth failed: {e}")
    sys.exit(1)

# ── 2. Test every SDK method ───────────────────────────────────────
print("═" * 70)
print("  TESTING ALL CLOB SDK METHODS")
print("═" * 70)

tests = []

def try_method(name, fn):
    t0 = time.time()
    try:
        result = fn()
        ms = (time.time() - t0) * 1000
        r = str(result)[:60]
        tests.append((name, 200, ms))
        print(f"  ✅ 200 {ms:5.0f}ms  {name:40s} → {r}")
    except Exception as e:
        ms = (time.time() - t0) * 1000
        err = str(e)
        if "403" in err:
            code = 403
            tag = "🛑 403"
        elif "404" in err:
            code = 404
            tag = "⚠️  404"
        elif "400" in err:
            code = 400
            tag = "⚠️  400"
        elif "500" in err:
            code = 500
            tag = "⚠️  500"
        else:
            code = -1
            tag = "⚠️  ERR"
        tests.append((name, code, ms))
        print(f"  {tag} {ms:5.0f}ms  {name:40s} → {err[:70]}")

# ── READ endpoints ──
print("\n── READ (no auth needed for some) ──")
try_method("get_open_orders()",             lambda: clob.get_open_orders())
try_method("get_trades()",                  lambda: clob.get_trades())
try_method("get_last_trades_prices()",      lambda: clob.get_last_trades_prices())

# Use a dummy token for token-specific endpoints
dummy = "0" * 66
try_method("get_order_book(dummy)",         lambda: clob.get_order_book(dummy))
try_method("get_last_trade_price(dummy)",   lambda: clob.get_last_trade_price(dummy))
try_method("is_order_scoring(dummy)",       lambda: clob.is_order_scoring(dummy))
try_method("are_orders_scoring()",          lambda: clob.are_orders_scoring())

# ── CANCEL/DELETE endpoints ──
print("\n── CANCEL/DELETE endpoints ──")
try_method("cancel_all()",                  lambda: clob.cancel_all())
try_method("cancel_orders([])",             lambda: clob.cancel_orders([]))
try_method("cancel_market_orders(dummy)",   lambda: clob.cancel_market_orders(dummy))

# ── RAW HTTP tests (bypass SDK, hit endpoints directly) ──
print("\n── RAW HTTP (bypass SDK) ──")

# Get auth headers from the SDK's internal session
# The SDK uses HMAC auth headers — we'll use the SDK's internal client
try:
    # Try raw POST to /order with empty body
    internal = clob  # the SDK instance
    
    # Method 1: raw httpx POST to /order 
    client = httpx.Client(timeout=5.0)
    
    # Build auth headers same way SDK does
    from py_clob_client_v2.headers.headers import create_level_2_headers
    headers = create_level_2_headers(
        clob.signer, clob.creds, 
    )
    
    t0 = time.time()
    try:
        r = client.post(f"{CLOB_HOST}/order", headers=headers, json={})
        ms = (time.time() - t0) * 1000
        tests.append(("POST /order (empty body)", r.status_code, ms))
        if r.status_code == 403:
            print(f"  🛑 403 {ms:5.0f}ms  {'POST /order (empty body)':40s} → {r.text[:70]}")
        else:
            print(f"  ✅ {r.status_code} {ms:5.0f}ms  {'POST /order (empty body)':40s} → {r.text[:70]}")
    except Exception as e:
        ms = (time.time() - t0) * 1000
        print(f"  ⚠️  ERR {ms:5.0f}ms  {'POST /order (empty body)':40s} → {e}")
    
    # Method 2: GET /tick-size with a dummy condition
    t0 = time.time()
    try:
        r = client.get(f"{CLOB_HOST}/tick-size", params={"token_id": dummy})
        ms = (time.time() - t0) * 1000
        tests.append(("GET /tick-size (dummy)", r.status_code, ms))
        tag = "🛑 403" if r.status_code == 403 else f"{'✅' if r.status_code == 200 else '⚠️ '} {r.status_code}"
        print(f"  {tag} {ms:5.0f}ms  {'GET /tick-size (dummy)':40s} → {r.text[:70]}")
    except Exception as e:
        print(f"  ⚠️  ERR         {'GET /tick-size (dummy)':40s} → {e}")

    # Method 3: POST /orders (batch) with empty list
    t0 = time.time()
    try:
        r = client.post(f"{CLOB_HOST}/orders", headers=headers, json=[])
        ms = (time.time() - t0) * 1000
        tests.append(("POST /orders (empty batch)", r.status_code, ms))
        tag = "🛑 403" if r.status_code == 403 else f"{'✅' if r.status_code == 200 else '⚠️ '} {r.status_code}"
        print(f"  {tag} {ms:5.0f}ms  {'POST /orders (empty batch)':40s} → {r.text[:70]}")
    except Exception as e:
        print(f"  ⚠️  ERR         {'POST /orders (empty batch)':40s} → {e}")

    # Method 4: GET /rewards (if exists)
    t0 = time.time()
    try:
        r = client.get(f"{CLOB_HOST}/rewards", headers=headers)
        ms = (time.time() - t0) * 1000
        tag = "🛑 403" if r.status_code == 403 else f"{'✅' if r.status_code == 200 else '⚠️ '} {r.status_code}"
        print(f"  {tag} {ms:5.0f}ms  {'GET /rewards':40s} → {r.text[:70]}")
    except Exception as e:
        print(f"  ⚠️  ERR         {'GET /rewards':40s} → {e}")

    # Method 5: POST /auth/derive-api-key (we know this works)
    t0 = time.time()
    try:
        r = client.get(f"{CLOB_HOST}/auth/derive-api-key", headers=headers)
        ms = (time.time() - t0) * 1000
        tag = "🛑 403" if r.status_code == 403 else f"{'✅' if r.status_code == 200 else '⚠️ '} {r.status_code}"
        print(f"  {tag} {ms:5.0f}ms  {'GET /auth/derive-api-key':40s} → ok")
    except Exception as e:
        print(f"  ⚠️  ERR         {'GET /auth/derive-api-key':40s} → {e}")

    # Method 6: GET /trade-notifications
    t0 = time.time()
    try:
        r = client.get(f"{CLOB_HOST}/trade-notifications", headers=headers)
        ms = (time.time() - t0) * 1000
        tag = "🛑 403" if r.status_code == 403 else f"{'✅' if r.status_code == 200 else '⚠️ '} {r.status_code}"
        print(f"  {tag} {ms:5.0f}ms  {'GET /trade-notifications':40s} → {r.text[:70]}")
    except Exception as e:
        print(f"  ⚠️  ERR         {'GET /trade-notifications':40s} → {e}")

    client.close()
    
except Exception as e:
    print(f"  ⚠️  Raw HTTP setup failed: {e}")

# ── 4. Summary ─────────────────────────────────────────────────────
print(f"\n{'═'*70}")
print(f"  SUMMARY")
print(f"{'═'*70}")

ok_eps = [t for t in tests if t[1] == 200]
blocked_eps = [t for t in tests if t[1] == 403]
err_eps = [t for t in tests if t[1] not in (200, 403)]

print(f"\n  ✅ PASS (200):  {len(ok_eps)}")
for t in ok_eps:
    print(f"     {t[0]}")

if blocked_eps:
    print(f"\n  🛑 BLOCKED (403):  {len(blocked_eps)}")
    for t in blocked_eps:
        print(f"     {t[0]:45s} ({t[2]:.0f}ms)")
    
    # Find the LIGHTEST 403 endpoint (fastest response)
    fastest_403 = min(blocked_eps, key=lambda x: x[2])
    print(f"\n  💡 BEST FOR STARTUP CHECK: {fastest_403[0]} ({fastest_403[2]:.0f}ms)")
    print(f"     Fastest 403 response — use this in bot preflight.")

if err_eps:
    print(f"\n  ⚠️  ERRORS:  {len(err_eps)}")
    for t in err_eps:
        print(f"     {t[0]:45s} (status={t[1]})")
