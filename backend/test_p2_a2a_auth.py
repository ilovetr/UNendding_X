"""
P2: A2A SKILL Token 校验测试
防绕过机制：验证 A2A 端点强制校验 SKILL Token
"""
import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_p2_a2a.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///test_p2_a2a.db"
os.environ["SECRET_KEY"] = "p2-test-secret-key"

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
    print("P2: A2A SKILL Token 校验测试")
    print("=" * 60)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    ok("DB: tables created")

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:

        # ── Setup: two agents ────────────────────────────────────────────────────
        # Agent-Beta: owns abilities
        r = await client.post("/api/auth/register", json={
            "name": "Agent-Beta",
            "endpoint": "http://beta.example.com",
        })
        assert r.status_code == 200, f"Register Beta: {r.text}"
        beta = r.json()
        beta_id = beta["id"]
        beta_key = beta["api_key"]

        # Agent-Alpha: will try to call Beta
        r = await client.post("/api/auth/register", json={
            "name": "Agent-Alpha",
            "endpoint": "http://alpha.example.com",
        })
        assert r.status_code == 200
        alpha = r.json()
        alpha_id = alpha["id"]
        alpha_key = alpha["api_key"]

        # Login to get JWT
        r = await client.post("/api/auth/token", json={"id": beta_id, "api_key": beta_key})
        beta_token = r.json()["access_token"]
        ok(f"Setup: Beta JWT obtained")

        r = await client.post("/api/auth/token", json={"id": alpha_id, "api_key": alpha_key})
        alpha_token = r.json()["access_token"]
        ok(f"Setup: Alpha JWT obtained")

        # ── Create abilities ─────────────────────────────────────────────────────
        # Public ability
        r = await client.post(
            "/api/abilities",
            json={
                "name": "public-hello",
                "description": "Public greeting",
                "version": "1.0.0",
                "definition": {},
                "is_public": True,
            },
            headers={"Authorization": f"Bearer {beta_token}"},
        )
        assert r.status_code == 201, f"Create public ability: {r.text}"
        public_ability = r.json()
        public_ability_id = public_ability["id"]
        ok(f"Setup: Public ability created id={public_ability_id[:8]}...")

        # Protected ability
        r = await client.post(
            "/api/abilities",
            json={
                "name": "protected-hello",
                "description": "Protected greeting",
                "version": "1.0.0",
                "definition": {},
                "is_public": False,
            },
            headers={"Authorization": f"Bearer {beta_token}"},
        )
        assert r.status_code == 201
        protected_ability = r.json()
        protected_ability_id = protected_ability["id"]
        ok(f"Setup: Protected ability created id={protected_ability_id[:8]}...")

        # ── Test 1: Send message without token (public ability) ─────────────────
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
            ok("T1: No token + public ability = SUCCESS")
        else:
            fail(f"T1: No token + public ability = {r.status_code} (expected 200)")

        # ── Test 2: Send message without token (protected ability) ──────────────
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
            ok("T2: No token + protected ability = 403 Forbidden")
        else:
            fail(f"T2: No token + protected ability = {r.status_code} (expected 403)")

        # ── Test 3: Send message with invalid token ───────────────────────────────
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": "invalid_token_123"},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                },
                "abilityId": protected_ability_id,
            },
        )
        if r.status_code == 401:
            ok("T3: Invalid token = 401 Unauthorized")
        else:
            fail(f"T3: Invalid token = {r.status_code} (expected 401)")

        # ── Test 4: Install SKILL token for protected ability ───────────────────
        r = await client.post(
            "/api/skills/install",
            headers={"Authorization": f"Bearer {alpha_token}"},
            json={
                "skill_name": "call-protected",
                "ability_ids": [protected_ability_id],
            },
        )
        assert r.status_code == 201, f"Install skill: {r.text}"
        skill_token = r.json()["token"]
        ok(f"T4: SKILL token installed")

        # ── Test 5: Send message with valid token (protected ability) ───────────
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": skill_token},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello from Alpha"}],
                },
                "abilityId": protected_ability_id,
            },
        )
        if r.status_code == 200:
            ok("T5: Valid token + protected ability = SUCCESS")
        else:
            fail(f"T5: Valid token + protected ability = {r.status_code}")

        # ── Test 6: Revoke SKILL token, then use it ─────────────────────────────
        # Get token ID from my-tokens
        r = await client.get(
            "/api/skills/my-tokens",
            headers={"Authorization": f"Bearer {alpha_token}"},
        )
        tokens = r.json()
        assert len(tokens) > 0
        token_id = tokens[0]["id"]

        # Revoke
        r = await client.delete(
            f"/api/skills/{token_id}",
            headers={"Authorization": f"Bearer {alpha_token}"},
        )
        assert r.status_code == 204
        ok("T6: SKILL token revoked")

        # Try to use revoked token
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": skill_token},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                },
                "abilityId": protected_ability_id,
            },
        )
        if r.status_code == 401:
            ok("T6: Revoked token = 401 Unauthorized (bypass prevented!)")
        else:
            fail(f"T6: Revoked token = {r.status_code} (expected 401)")

        # ── Test 7: Token without permission on ability ───────────────────────────
        # Install token for public ability only
        r = await client.post(
            "/api/skills/install",
            headers={"Authorization": f"Bearer {alpha_token}"},
            json={
                "skill_name": "call-public-only",
                "ability_ids": [public_ability_id],
            },
        )
        assert r.status_code == 201
        public_only_token = r.json()["token"]

        # Try to use this token on protected ability
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": public_only_token},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                },
                "abilityId": protected_ability_id,
            },
        )
        if r.status_code == 403:
            ok("T7: Token without permission = 403 Forbidden")
        else:
            fail(f"T7: Token without permission = {r.status_code} (expected 403)")

        # ── Test 8: Streaming endpoint also checks token ─────────────────────────
        r = await client.post(
            "/a2a/message:stream",
            headers={"X-SKILL-TOKEN": "bad_token"},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                },
                "abilityId": protected_ability_id,
            },
        )
        if r.status_code == 401:
            ok("T8: Streaming + invalid token = 401")
        else:
            fail(f"T8: Streaming + invalid token = {r.status_code} (expected 401)")

    # ── Summary ─────────────────────────────────────────────────────────────────
    print("=" * 60)
    print(f"Results: {sum(1 for r in results if r[0])}/{len(results)} passed")
    print("=" * 60)

    # Exit with error if any test failed
    if any(not r for r in results):
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
