"""
AgentHub CLI End-to-End Test
SQLite mode - no Docker/PostgreSQL required

Tests the full API flow: register -> login -> groups -> abilities -> skills -> audit -> a2a
Run from: cd backend && python test_cli_e2e.py
"""
import asyncio
import os
import sys

# Force UTF-8 on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Override DB to SQLite BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_cli_e2e.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./test_cli_e2e.db"
os.environ["SECRET_KEY"] = "cli_test_secret_key_for_verification_only"

import httpx
from httpx import ASGITransport
from app.main import app
from app.database import engine, Base
from app.config import settings

assert "sqlite" in settings.DATABASE_URL, f"DB URL wrong: {settings.DATABASE_URL}"

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []


def ok(label):
    print(f"  {PASS} {label}")
    results.append((True, label))


def fail(label, detail=""):
    print(f"  {FAIL} {label}: {detail}")
    results.append((False, label))


async def main():
    print("=" * 60)
    print("AgentHub CLI End-to-End API Verification")
    print("=" * 60)

    # Init variables
    agent_id = ""
    api_key = ""
    ability_id = ""
    group_id = ""
    invite_code = ""
    skill_token = ""
    token_id = ""

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Start backend using httpx ASGI transport
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        # ─── 1. Health Check ────────────────────────────
        print("\n--- 1. Health Check ---")
        r = await client.get("/health")
        if r.status_code == 200 and r.json()["status"] == "healthy":
            ok("GET /health -> healthy")
        else:
            fail("GET /health", f"status={r.status_code}")

        # ─── 2. Agent Card ─────────────────────────────
        print("\n--- 2. Agent Card ---")
        r = await client.get("/.well-known/agent.json")
        if r.status_code == 200 and "name" in r.json():
            ok(f"Agent Card: {r.json()['name']}")
        else:
            fail("Agent Card", r.text)

        # ─── 3. Register Agent ──────────────────────────
        print("\n--- 3. Auth: Register ---")
        r = await client.post("/api/auth/register", json={"name": "cli-test-agent"})
        if r.status_code == 200:
            reg = r.json()
            agent_id = reg["id"]
            api_key = reg["api_key"]
            ok(f"Register agent: id={agent_id[:8]}")
        else:
            fail("Register agent", r.text)
            return

        # ─── 4. Login / Get Token ───────────────────────
        print("\n--- 4. Auth: Login ---")
        r = await client.post("/api/auth/token", json={
            "id": agent_id, "api_key": api_key,
        })
        if r.status_code == 200 and "access_token" in r.json():
            token = r.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            ok("Login, got JWT token")
        else:
            fail("Login", r.text)
            return

        # ─── 5. Groups: Create ──────────────────────────
        print("\n--- 5. Groups: Create ---")
        r = await client.post("/api/groups", json={
            "name": "CLI测试群组",
            "description": "CLI e2e test group",
            "privacy": "public",
        }, headers=headers)
        if r.status_code == 201:
            group = r.json()
            group_id = group["id"]
            invite_code = group.get("invite_code", "")
            ok(f"Create group: {group['name']} (code={invite_code})")
        else:
            fail("Create group", r.text)

        # ─── 6. Groups: List ────────────────────────────
        print("\n--- 6. Groups: List ---")
        r = await client.get("/api/groups", headers=headers)
        if r.status_code == 200 and len(r.json()) > 0:
            ok(f"List groups: found {len(r.json())}")
        else:
            fail("List groups", r.text)

        # ─── 7. Groups: Mine ────────────────────────────
        print("\n--- 7. Groups: Mine ---")
        r = await client.get("/api/groups/mine", headers=headers)
        if r.status_code == 200:
            ok(f"My groups: {len(r.json())}")
        else:
            fail("My groups", r.text)

        # ─── 8. Abilities: Register ─────────────────────
        print("\n--- 8. Abilities: Register ---")
        r = await client.post("/api/abilities", json={
            "name": "cli-test-ability",
            "description": "A test ability",
            "version": "1.0.0",
            "definition": {"input": "text", "output": "result"},
        }, headers=headers)
        if r.status_code == 201:
            ability = r.json()
            ability_id = ability["id"]
            ok(f"Register ability: {ability['name']} v{ability['version']}")
        else:
            fail("Register ability", r.text)

        # ─── 9. Abilities: List ─────────────────────────
        print("\n--- 9. Abilities: List ---")
        r = await client.get("/api/abilities", headers=headers)
        if r.status_code == 200 and len(r.json()) > 0:
            ok(f"List abilities: found {len(r.json())}")
        else:
            fail("List abilities", r.text)

        # ─── 10. Abilities: Mine ────────────────────────
        print("\n--- 10. Abilities: Mine ---")
        r = await client.get("/api/abilities/mine", headers=headers)
        if r.status_code == 200 and len(r.json()) > 0:
            ok(f"My abilities: {len(r.json())}")
        else:
            fail("My abilities", r.text)

        # ─── 11. Skills: Install ────────────────────────
        print("\n--- 11. Skills: Install ---")
        r = await client.post("/api/skills/install", json={
            "skill_name": "cli-test-skill",
            "version": "1.0.0",
            "ability_ids": [ability_id] if ability_id else [],
        }, headers=headers)
        if r.status_code == 201:
            skill_data = r.json()
            skill_token = skill_data.get("token", "")
            token_id = skill_data.get("token_id", "")
            ok(f"Install skill: {skill_data['skill_name']}")
        else:
            fail("Install skill", r.text)

        # ─── 12. Skills: Verify ─────────────────────────
        print("\n--- 12. Skills: Verify ---")
        if skill_token:
            r = await client.post("/api/skills/verify", json={"token": skill_token})
            if r.status_code == 200 and r.json().get("valid"):
                ok("Verify skill token: VALID")
            else:
                fail("Verify skill token", r.text)
        else:
            fail("Verify skill token: no token available")

        # ─── 13. Skills: Check ──────────────────────────
        print("\n--- 13. Skills: Check ---")
        if skill_token and ability_id:
            r = await client.post("/api/skills/check", json={
                "token": skill_token, "ability_id": ability_id,
            })
            if r.status_code == 200 and r.json().get("allowed"):
                ok("Check skill permission: ALLOWED")
            else:
                fail("Check skill permission", r.text)
        else:
            fail("Check skill permission: missing token or ability_id")

        # ─── 14. Skills: My Tokens ──────────────────────
        print("\n--- 14. Skills: My Tokens ---")
        r = await client.get("/api/skills/my-tokens", headers=headers)
        if r.status_code == 200 and len(r.json()) > 0:
            ok(f"My tokens: {len(r.json())}")
        else:
            fail("My tokens", r.text)

        # ─── 15. Skills: Revoke ─────────────────────────
        print("\n--- 15. Skills: Revoke ---")
        if token_id:
            r = await client.delete(f"/api/skills/{token_id}", headers=headers)
            if r.status_code in (200, 204):
                ok("Revoke skill token")
            else:
                fail("Revoke skill token", f"status={r.status_code}")
        else:
            fail("Revoke skill token: no token_id")

        # ─── 16. Audit: List ────────────────────────────
        print("\n--- 16. Audit: List ---")
        r = await client.get("/api/audit", headers=headers)
        if r.status_code == 200:
            logs = r.json()
            ok(f"Audit logs: {len(logs)} entries")
        else:
            fail("Audit logs", r.text)

        # ─── 17. A2A: Message ───────────────────────────
        print("\n--- 17. A2A: Message ---")
        r = await client.post("/a2a/message:send", json={
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Hello from CLI test"}],
            },
        }, headers=headers)
        if r.status_code == 200:
            task_id = r.json().get("taskId", r.json().get("task_id", ""))
            ok(f"A2A message sent: task={task_id[:8] if task_id else 'N/A'}")
        else:
            fail("A2A message", r.text)

    # ─── Summary ────────────────────────────────────────
    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r[0])
    total = len(results)
    print(f"Results: {passed}/{total} passed")
    if passed < total:
        print("Failed:")
        for ok_flag, label in results:
            if not ok_flag:
                print(f"  - {label}")
    print("=" * 60)

    # Cleanup
    await engine.dispose()
    db_file = "test_cli_e2e.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
