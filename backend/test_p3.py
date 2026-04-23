"""
P3 end-to-end verification: Permissions + SKILL Tokens + Audit Logs
Covers: install / verify / check / revoke / audit mine
"""
import asyncio
import os
import sys

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_p3.db"
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-p3-verification-only")
os.environ.setdefault("AGENT_ENDPOINT", "http://localhost:8000")

import httpx
from httpx import ASGITransport
from app.main import app
from app.database import engine, Base

BASE = "http://test"


# ── helpers ───────────────────────────────────────────────────────────────────

PASS = 0
FAIL = 0

def ok(label):
    global PASS
    PASS += 1
    print(f"[PASS] {label}")

def fail(label, info=""):
    global FAIL
    FAIL += 1
    print(f"[FAIL] {label}  {info}")


async def register(client, name):
    r = await client.post("/api/auth/register", json={"name": name})
    assert r.status_code == 200, f"register {name} failed: {r.text}"
    d = r.json()
    return d["id"], d["api_key"]


async def login(client, agent_id, api_key):
    r = await client.post("/api/auth/token", json={"id": agent_id, "api_key": api_key})
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── main ──────────────────────────────────────────────────────────────────────

async def main():
    # Setup DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:

        # ── Setup: two agents ────────────────────────────────────────────────
        id_a, key_a = await register(c, "P3-Alpha")
        id_b, key_b = await register(c, "P3-Beta")
        tok_a = await login(c, id_a, key_a)
        tok_b = await login(c, id_b, key_b)

        # ── Setup: ability owned by Alpha ────────────────────────────────────
        r = await c.post(
            "/api/abilities",
            json={
                "name": "summarize",
                "description": "text summarizer",
                "version": "1.0.0",
                "definition": {"input": "text", "output": "summary"},
            },
            headers=auth(tok_a),
        )
        assert r.status_code == 201, f"ability register: {r.text}"
        ability_id = r.json()["id"]

        # ── T1: Install skill token (no abilities) ───────────────────────────
        r = await c.post(
            "/api/skills/install",
            json={"skill_name": "my-skill", "version": "1.0.0"},
            headers=auth(tok_a),
        )
        if r.status_code == 201 and "token" in r.json():
            ok("T01: skill install (empty permissions)")
            token_a = r.json()["token"]
            token_id_a = r.json()["token_id"]
        else:
            fail("T01: skill install (empty permissions)", r.text)
            return

        # ── T2: Install skill token WITH ability ─────────────────────────────
        r = await c.post(
            "/api/skills/install",
            json={"skill_name": "able-skill", "ability_ids": [ability_id], "version": "1.1.0"},
            headers=auth(tok_a),
        )
        if r.status_code == 201 and ability_id in r.json()["permissions"]:
            ok("T02: skill install with ability permission")
            token_with_perm = r.json()["token"]
            token_id_with_perm = r.json()["token_id"]
        else:
            fail("T02: skill install with ability permission", r.text)
            return

        # ── T3: Verify valid token ───────────────────────────────────────────
        r = await c.post("/api/skills/verify", json={"token": token_a})
        d = r.json()
        if d["valid"] and d["skill_name"] == "my-skill":
            ok("T03: verify valid token")
        else:
            fail("T03: verify valid token", str(d))

        # ── T4: Verify garbage token ─────────────────────────────────────────
        r = await c.post("/api/skills/verify", json={"token": "not.a.token"})
        if not r.json()["valid"]:
            ok("T04: verify garbage token -> invalid")
        else:
            fail("T04: verify garbage token -> invalid", r.text)

        # ── T5: Check permission - has it ────────────────────────────────────
        r = await c.post(
            "/api/skills/check",
            json={"token": token_with_perm, "ability_id": ability_id},
        )
        if r.json()["allowed"]:
            ok("T05: check permission -> allowed")
        else:
            fail("T05: check permission -> allowed", r.text)

        # ── T6: Check permission - doesn't have it ───────────────────────────
        r = await c.post(
            "/api/skills/check",
            json={"token": token_a, "ability_id": ability_id},
        )
        d = r.json()
        if not d["allowed"] and d["reason"] == "no_permission":
            ok("T06: check permission -> no_permission")
        else:
            fail("T06: check permission -> no_permission", str(d))

        # ── T7: Check expired/invalid token ──────────────────────────────────
        r = await c.post(
            "/api/skills/check",
            json={"token": "garbage.token.here", "ability_id": ability_id},
        )
        if not r.json()["allowed"] and r.json()["reason"] == "invalid_token":
            ok("T07: check invalid token -> invalid_token")
        else:
            fail("T07: check invalid token -> invalid_token", r.text)

        # ── T8: List my tokens ───────────────────────────────────────────────
        r = await c.get("/api/skills/my-tokens", headers=auth(tok_a))
        if r.status_code == 200 and len(r.json()) == 2:
            ok("T08: list my tokens -> 2 tokens")
        else:
            fail("T08: list my tokens -> 2 tokens", r.text)

        # ── T9: Beta cannot revoke Alpha's token ─────────────────────────────
        r = await c.delete(f"/api/skills/{token_id_a}", headers=auth(tok_b))
        if r.status_code == 403:
            ok("T09: Beta revoke Alpha token -> 403")
        else:
            fail("T09: Beta revoke Alpha token -> 403", r.text)

        # ── T10: Alpha revokes own token ─────────────────────────────────────
        r = await c.delete(f"/api/skills/{token_id_a}", headers=auth(tok_a))
        if r.status_code == 204:
            ok("T10: Alpha revokes own token -> 204")
        else:
            fail("T10: Alpha revokes own token -> 204", r.text)

        # ── T11: Revoked token verify -> revoked=True ────────────────────────
        r = await c.post("/api/skills/verify", json={"token": token_a})
        d = r.json()
        if not d["valid"] and d["revoked"]:
            ok("T11: revoked token verify -> invalid+revoked")
        else:
            fail("T11: revoked token verify -> invalid+revoked", str(d))

        # ── T12: Check revoked token permission ──────────────────────────────
        r = await c.post(
            "/api/skills/check",
            json={"token": token_a, "ability_id": ability_id},
        )
        d = r.json()
        if not d["allowed"] and d["reason"] == "token_revoked":
            ok("T12: check revoked token -> token_revoked")
        else:
            fail("T12: check revoked token -> token_revoked", str(d))

        # ── T13: My tokens now 1 (after revoke) ─────────────────────────────
        r = await c.get("/api/skills/my-tokens", headers=auth(tok_a))
        if r.status_code == 200 and len(r.json()) == 1:
            ok("T13: my tokens after revoke -> 1")
        else:
            fail("T13: my tokens after revoke -> 1", r.text)

        # ── T14: Revoke non-existent token -> 404 ────────────────────────────
        import uuid as uuidmod
        r = await c.delete(f"/api/skills/{uuidmod.uuid4()}", headers=auth(tok_a))
        if r.status_code == 404:
            ok("T14: revoke non-existent -> 404")
        else:
            fail("T14: revoke non-existent -> 404", r.text)

        # ── T15: Audit /mine returns entries ─────────────────────────────────
        r = await c.get("/api/audit/mine", headers=auth(tok_a))
        logs = r.json()
        if r.status_code == 200 and len(logs) >= 1:
            ok(f"T15: audit /mine -> {len(logs)} entries")
        else:
            fail("T15: audit /mine -> entries", r.text)

        # ── T16: Audit /mine filter by action ────────────────────────────────
        r = await c.get("/api/audit/mine?action=agent_register", headers=auth(tok_a))
        logs = r.json()
        if r.status_code == 200 and all(l["action"] == "agent_register" for l in logs):
            ok(f"T16: audit /mine filter action=agent_register -> {len(logs)} entries, all match")
        else:
            fail("T16: audit /mine filter action=agent_register", r.text)

        # ── T17: Global audit list (no auth required currently) ──────────────
        r = await c.get("/api/audit")
        if r.status_code == 200 and isinstance(r.json(), list):
            ok(f"T17: global audit list -> {len(r.json())} total entries")
        else:
            fail("T17: global audit list", r.text)

        # ── T18: Install skill for Beta to verify isolation ──────────────────
        r = await c.post(
            "/api/skills/install",
            json={"skill_name": "beta-skill"},
            headers=auth(tok_b),
        )
        if r.status_code == 201:
            beta_token_id = r.json()["token_id"]
            ok("T18: Beta installs own skill token")
        else:
            fail("T18: Beta installs own skill token", r.text)
            beta_token_id = None

        # ── T19: Alpha cannot revoke Beta's token ────────────────────────────
        if beta_token_id:
            r = await c.delete(f"/api/skills/{beta_token_id}", headers=auth(tok_a))
            if r.status_code == 403:
                ok("T19: Alpha cannot revoke Beta token -> 403")
            else:
                fail("T19: Alpha cannot revoke Beta token -> 403", r.text)

        # ── T20: Beta my-tokens only shows Beta's token ──────────────────────
        r = await c.get("/api/skills/my-tokens", headers=auth(tok_b))
        d = r.json()
        if r.status_code == 200 and len(d) == 1 and d[0]["skill_name"] == "beta-skill":
            ok("T20: my-tokens isolation: Beta sees only own token")
        else:
            fail("T20: my-tokens isolation", r.text)

    # Cleanup
    try:
        if os.path.exists("test_p3.db"):
            os.remove("test_p3.db")
    except PermissionError:
        pass

    total = PASS + FAIL
    print(f"\n{'ALL PASS' if FAIL == 0 else 'FAILURES'}: {PASS}/{total}")
    if FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
