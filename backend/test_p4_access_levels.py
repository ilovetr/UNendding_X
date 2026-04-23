"""
P4: 三层权限体系测试
验证: PUBLIC / PROTECTED / LIMITED 三种访问级别
"""
import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_p4_access.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///test_p4_access.db"
os.environ["SECRET_KEY"] = "p4-access-test-secret"

import httpx
from httpx import ASGITransport
from app.main import app
from app.database import engine, Base

BASE = "http://test"
PASS = "[PASS]"
FAIL = "[FAIL]"
results = []


def ok(label):
    print(f"{PASS} {label}")
    results.append((True, label))


def fail(label, detail=""):
    print(f"{FAIL} {label}: {detail}")
    results.append((False, label))


async def main():
    print("=" * 60)
    print("P4: 三层权限体系测试")
    print("=" * 60)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    ok("DB: tables created")

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:

        # ── Setup: Agent-Beta (ability owner), Agent-Alpha (caller) ───────────────
        r = await client.post("/api/auth/register", json={
            "name": "Agent-Beta",
            "endpoint": "http://beta.example.com",
        })
        assert r.status_code == 200
        beta = r.json()
        beta_id, beta_key = beta["id"], beta["api_key"]

        r = await client.post("/api/auth/register", json={
            "name": "Agent-Alpha",
            "endpoint": "http://alpha.example.com",
        })
        assert r.status_code == 200
        alpha = r.json()
        alpha_id, alpha_key = alpha["id"], alpha["api_key"]

        # Login
        r = await client.post("/api/auth/token", json={"id": beta_id, "api_key": beta_key})
        beta_token = r.json()["access_token"]
        r = await client.post("/api/auth/token", json={"id": alpha_id, "api_key": alpha_key})
        alpha_token = r.json()["access_token"]

        # ── Create three abilities with different access levels ─────────────────

        # L1: PUBLIC - no auth needed
        r = await client.post(
            "/api/abilities",
            json={
                "name": "public-service",
                "description": "Public greeting service",
                "version": "1.0.0",
                "definition": {},
                "access_level": "public",
            },
            headers={"Authorization": f"Bearer {beta_token}"},
        )
        assert r.status_code == 201, f"Create public ability: {r.text}"
        public_ability = r.json()
        public_ability_id = public_ability["id"]
        ok(f"Setup: PUBLIC ability created id={public_ability_id[:8]}...")

        # L2: PROTECTED - token required, unlimited
        r = await client.post(
            "/api/abilities",
            json={
                "name": "protected-api",
                "description": "Protected API",
                "version": "1.0.0",
                "definition": {},
                "access_level": "protected",
            },
            headers={"Authorization": f"Bearer {beta_token}"},
        )
        assert r.status_code == 201
        protected_ability = r.json()
        protected_ability_id = protected_ability["id"]
        ok(f"Setup: PROTECTED ability created id={protected_ability_id[:8]}...")

        # L3: LIMITED - token required, quota=3
        r = await client.post(
            "/api/abilities",
            json={
                "name": "limited-api",
                "description": "Limited API with quota",
                "version": "1.0.0",
                "definition": {},
                "access_level": "limited",
                "quota_per_token": 3,
            },
            headers={"Authorization": f"Bearer {beta_token}"},
        )
        assert r.status_code == 201
        limited_ability = r.json()
        limited_ability_id = limited_ability["id"]
        ok(f"Setup: LIMITED ability (quota=3) created id={limited_ability_id[:8]}...")

        # ── T1: PUBLIC ability - no token required ────────────────────────────────
        r = await client.post(
            "/a2a/message:send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                },
                "abilityId": public_ability_id,
            },
        )
        if r.status_code == 200:
            ok("T1: PUBLIC ability - no token = SUCCESS")
        else:
            fail(f"T1: PUBLIC ability - no token = {r.status_code}")

        # ── T2: PROTECTED ability - no token = 403 ───────────────────────────────
        r = await client.post(
            "/a2a/message:send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                },
                "abilityId": protected_ability_id,
            },
        )
        if r.status_code == 403:
            ok("T2: PROTECTED ability - no token = 403")
        else:
            fail(f"T2: PROTECTED ability - no token = {r.status_code}")

        # ── T3: LIMITED ability - no token = 403 ─────────────────────────────────
        r = await client.post(
            "/a2a/message:send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                },
                "abilityId": limited_ability_id,
            },
        )
        if r.status_code == 403:
            ok("T3: LIMITED ability - no token = 403")
        else:
            fail(f"T3: LIMITED ability - no token = {r.status_code}")

        # ── T4: Install SKILL token for PROTECTED ability ──────────────────────────
        r = await client.post(
            "/api/skills/install",
            headers={"Authorization": f"Bearer {alpha_token}"},
            json={
                "skill_name": "call-protected",
                "ability_ids": [protected_ability_id],
            },
        )
        assert r.status_code == 201, f"Install skill: {r.text}"
        protected_token = r.json()["token"]
        ok("T4: Installed SKILL token for PROTECTED ability")

        # ── T5: PROTECTED ability - valid token = SUCCESS ─────────────────────────
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": protected_token},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                },
                "abilityId": protected_ability_id,
            },
        )
        if r.status_code == 200:
            ok("T5: PROTECTED ability - valid token = SUCCESS")
        else:
            fail(f"T5: PROTECTED ability - valid token = {r.status_code}")

        # ── T6: Install SKILL token for LIMITED ability ───────────────────────────
        r = await client.post(
            "/api/skills/install",
            headers={"Authorization": f"Bearer {alpha_token}"},
            json={
                "skill_name": "call-limited",
                "ability_ids": [limited_ability_id],
            },
        )
        assert r.status_code == 201
        limited_token = r.json()["token"]
        ok("T6: Installed SKILL token for LIMITED ability")

        # ── T7: LIMITED ability - first call = SUCCESS (quota: 3→2) ─────────────
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": limited_token},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Call 1"}],
                },
                "abilityId": limited_ability_id,
            },
        )
        if r.status_code == 200:
            ok("T7: LIMITED ability - call 1/3 = SUCCESS")
        else:
            fail(f"T7: LIMITED ability - call 1 = {r.status_code}")

        # ── T8: LIMITED ability - second call = SUCCESS (quota: 2→1) ────────────
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": limited_token},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Call 2"}],
                },
                "abilityId": limited_ability_id,
            },
        )
        if r.status_code == 200:
            ok("T8: LIMITED ability - call 2/3 = SUCCESS")
        else:
            fail(f"T8: LIMITED ability - call 2 = {r.status_code}")

        # ── T9: LIMITED ability - third call = SUCCESS (quota: 1→0) ─────────────
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": limited_token},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Call 3"}],
                },
                "abilityId": limited_ability_id,
            },
        )
        if r.status_code == 200:
            ok("T9: LIMITED ability - call 3/3 = SUCCESS")
        else:
            fail(f"T9: LIMITED ability - call 3 = {r.status_code}")

        # ── T10: LIMITED ability - fourth call = 403 (quota exhausted!) ───────────
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": limited_token},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Call 4"}],
                },
                "abilityId": limited_ability_id,
            },
        )
        if r.status_code == 403 and "quota" in r.json().get("detail", "").lower():
            ok("T10: LIMITED ability - call 4/3 = 403 quota exhausted!")
        else:
            fail(f"T10: LIMITED ability - call 4 = {r.status_code} (expected 403 quota)")

        # ── T11: Install with custom quota override ──────────────────────────────
        r = await client.post(
            "/api/skills/install",
            headers={"Authorization": f"Bearer {alpha_token}"},
            json={
                "skill_name": "call-limited-5",
                "ability_ids": [limited_ability_id],
                "quota": 5,  # Override with 5
            },
        )
        assert r.status_code == 201
        custom_quota_token = r.json()["token"]
        ok("T11: Installed with custom quota=5")

        # ── T12: Custom quota - use 4 times (5→1) ───────────────────────────────
        for i in range(4):
            r = await client.post(
                "/a2a/message:send",
                headers={"X-SKILL-TOKEN": custom_quota_token},
                json={
                    "message": {
                        "role": "user",
                        "parts": [{"type": "text", "text": f"Call {i+1}"}],
                    },
                    "abilityId": limited_ability_id,
                },
            )
        ok("T12: Custom quota - 4 calls made (5→1)")

        # ── T13: Custom quota - 5th call = SUCCESS (1→0) ────────────────────────
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": custom_quota_token},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Call 5"}],
                },
                "abilityId": limited_ability_id,
            },
        )
        if r.status_code == 200:
            ok("T13: Custom quota - 5th call = SUCCESS")
        else:
            fail(f"T13: Custom quota - 5th call = {r.status_code}")

        # ── T14: Custom quota - 6th call = 403 ───────────────────────────────────
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": custom_quota_token},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Call 6"}],
                },
                "abilityId": limited_ability_id,
            },
        )
        if r.status_code == 403:
            ok("T14: Custom quota - 6th call = 403 quota exhausted!")
        else:
            fail(f"T14: Custom quota - 6th call = {r.status_code}")

        # ── T15: List abilities by access_level ──────────────────────────────────
        r = await client.get("/api/abilities?access_level=limited")
        if r.status_code == 200:
            abilities = r.json()
            limited_count = len([a for a in abilities if a["access_level"] == "limited"])
            ok(f"T15: Filter by access_level=limited -> {limited_count} abilities")
        else:
            fail(f"T15: Filter by access_level = {r.status_code}")

    # ── Summary ─────────────────────────────────────────────────────────────────
    print("=" * 60)
    print(f"Results: {sum(1 for r in results if r[0])}/{len(results)} passed")
    print("=" * 60)

    if any(not r for r in results):
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
