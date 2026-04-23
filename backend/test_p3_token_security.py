"""
P3: Token 安全测试
- 退出群聊 Token 级联 revoke
- 踢人 Token 级联 revoke
"""
import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_p3_token.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///test_p3_token.db"
os.environ["SECRET_KEY"] = "p3-token-test-secret"

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
    print("P3: Token 安全测试 - 退出/踢人时级联 Revoke")
    print("=" * 60)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    ok("DB: tables created")

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:

        # ── Setup: Agent-Beta (group owner), Agent-Alpha (member) ─────────────────
        r = await client.post("/api/auth/register", json={
            "name": "Agent-Beta",
            "endpoint": "http://beta.example.com",
        })
        if r.status_code != 200:
            fail(f"Setup: Register Beta = {r.status_code}: {r.text}")
            return
        beta = r.json()
        beta_id, beta_key = beta["id"], beta["api_key"]

        r = await client.post("/api/auth/register", json={
            "name": "Agent-Alpha",
            "endpoint": "http://alpha.example.com",
        })
        if r.status_code != 200:
            fail(f"Setup: Register Alpha = {r.status_code}: {r.text}")
            return
        alpha = r.json()
        alpha_id, alpha_key = alpha["id"], alpha["api_key"]

        # Login
        r = await client.post("/api/auth/token", json={"id": beta_id, "api_key": beta_key})
        beta_token = r.json()["access_token"]
        r = await client.post("/api/auth/token", json={"id": alpha_id, "api_key": alpha_key})
        alpha_token = r.json()["access_token"]

        # ── Create group and ability ────────────────────────────────────────────────
        r = await client.post(
            "/api/groups",
            json={
                "name": "Test Group",
                "description": "Test group for token security",
                "privacy": "public",
                "category": "tech",
            },
            headers={"Authorization": f"Bearer {beta_token}"},
        )
        if r.status_code != 201:
            fail(f"Setup: Create group = {r.status_code}: {r.text}")
            return
        group = r.json()
        group_id = group["id"]
        invite_code = group["invite_code"]
        ok(f"Setup: Group created id={group_id[:8]}...")

        # Register protected ability owned by Beta
        r = await client.post(
            "/api/abilities",
            json={
                "name": "protected-skill",
                "description": "Protected skill",
                "version": "1.0.0",
                "definition": {},
                "is_public": False,
            },
            headers={"Authorization": f"Bearer {beta_token}"},
        )
        if r.status_code != 201:
            fail(f"Setup: Create ability = {r.status_code}: {r.text}")
            return
        ability_id = r.json()["id"]

        # ── Alpha joins the group ──────────────────────────────────────────────────
        r = await client.post(
            "/api/groups/join",
            json={"invite_code": invite_code},
            headers={"Authorization": f"Bearer {alpha_token}"},
        )
        if r.status_code != 200:
            fail(f"Setup: Alpha join group = {r.status_code}: {r.text}")
            return
        ok("Setup: Alpha joined group")

        # ── Alpha installs a SKILL token for Beta's protected ability ───────────────
        r = await client.post(
            "/api/skills/install",
            headers={"Authorization": f"Bearer {alpha_token}"},
            json={
                "skill_name": "use-beta-skill",
                "ability_ids": [ability_id],
                "group_id": group_id,
            },
        )
        if r.status_code != 201:
            fail(f"Setup: Install skill = {r.status_code}: {r.text}")
            return
        skill_token = r.json()["token"]
        ok("Setup: Alpha installed SKILL token for group")

        # ── T1: Verify token works BEFORE leaving ───────────────────────────────────
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": skill_token},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                },
                "abilityId": ability_id,
            },
        )
        if r.status_code == 200:
            ok("T1: Token works before leaving group")
        else:
            fail(f"T1: Token should work before leaving = {r.status_code}")

        # ── T2: Alpha leaves group, token should be revoked ────────────────────────
        r = await client.post(
            f"/api/groups/{group_id}/leave",
            headers={"Authorization": f"Bearer {alpha_token}"},
        )
        if r.status_code != 204:
            fail(f"T2: Leave group = {r.status_code}: {r.text}")
            return
        ok("T2: Alpha left group")

        # ── T3: Token should be REVOKED now ────────────────────────────────────────
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": skill_token},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                },
                "abilityId": ability_id,
            },
        )
        if r.status_code == 401:
            ok("T3: Token revoked after leaving = 401 (bypass prevented!)")
        else:
            fail(f"T3: Token should be revoked = {r.status_code}")

        # ── T4: Alpha rejoins and we test kick revocation ──────────────────────────
        r = await client.post(
            "/api/groups/join",
            json={"invite_code": invite_code},
            headers={"Authorization": f"Bearer {alpha_token}"},
        )
        if r.status_code != 200:
            fail(f"Setup: Alpha rejoin = {r.status_code}: {r.text}")
            return

        # Reinstall token
        r = await client.post(
            "/api/skills/install",
            headers={"Authorization": f"Bearer {alpha_token}"},
            json={
                "skill_name": "use-beta-skill-2",
                "ability_ids": [ability_id],
                "group_id": group_id,
            },
        )
        if r.status_code != 201:
            fail(f"Setup: Reinstall skill = {r.status_code}: {r.text}")
            return
        skill_token2 = r.json()["token"]

        # ── T5: Token works before kick ────────────────────────────────────────────
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": skill_token2},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                },
                "abilityId": ability_id,
            },
        )
        if r.status_code == 200:
            ok("T5: Token works before kick")
        else:
            fail(f"T5: Token should work before kick = {r.status_code}")

        # ── T6: Beta kicks Alpha out ───────────────────────────────────────────────
        r = await client.delete(
            f"/api/groups/{group_id}/members/{alpha_id}",
            headers={"Authorization": f"Bearer {beta_token}"},
        )
        if r.status_code != 204:
            fail(f"T6: Kick member = {r.status_code}: {r.text}")
            return
        ok("T6: Beta kicked Alpha from group")

        # ── T7: Alpha's token should be revoked ───────────────────────────────────
        r = await client.post(
            "/a2a/message:send",
            headers={"X-SKILL-TOKEN": skill_token2},
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                },
                "abilityId": ability_id,
            },
        )
        if r.status_code == 401:
            ok("T7: Token revoked after kick = 401 (bypass prevented!)")
        else:
            fail(f"T7: Token should be revoked after kick = {r.status_code}")

    # ── Summary ─────────────────────────────────────────────────────────────────
    print("=" * 60)
    print(f"Results: {sum(1 for r in results if r[0])}/{len(results)} passed")
    print("=" * 60)

    if any(not r for r in results):
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
