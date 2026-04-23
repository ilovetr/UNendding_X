"""
P2 End-to-End Verification: Groups + Abilities
Tests all group management and ability registration flows
"""
import asyncio
import os
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_p2.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./test_p2.db"
os.environ["SECRET_KEY"] = "p2_test_secret_key"

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


async def register_and_login(client, name: str) -> tuple[str, str, str]:
    """Helper: register agent and return (id, api_key, jwt)"""
    r = await client.post("/api/auth/register", json={"name": name})
    assert r.status_code == 200, f"Register {name}: {r.text}"
    data = r.json()
    agent_id = data["id"]
    api_key = data["api_key"]

    r = await client.post("/api/auth/token", json={"id": agent_id, "api_key": api_key})
    assert r.status_code == 200, f"Login {name}: {r.text}"
    jwt = r.json()["access_token"]
    return agent_id, api_key, jwt


async def main():
    print("=" * 60)
    print("AgentHub P2 End-to-End Verification")
    print("Groups + Abilities")
    print("=" * 60)

    # Setup DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    ok("DB: tables ready")

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:

        # ── Setup: register 3 agents ──────────────────────────────────────────
        alpha_id, _, alpha_jwt = await register_and_login(client, "Alpha")
        beta_id, _, beta_jwt = await register_and_login(client, "Beta")
        gamma_id, _, gamma_jwt = await register_and_login(client, "Gamma")
        ok("Auth: 3 agents registered (Alpha, Beta, Gamma)")

        auth_a = {"Authorization": f"Bearer {alpha_jwt}"}
        auth_b = {"Authorization": f"Bearer {beta_jwt}"}
        auth_g = {"Authorization": f"Bearer {gamma_jwt}"}

        # ── 1. Create group ───────────────────────────────────────────────────
        r = await client.post("/api/groups", json={
            "name": "AI Research",
            "description": "Group for AI research agents",
            "privacy": "public",
            "category": "ai",
        }, headers=auth_a)
        assert r.status_code == 201, f"Create group: {r.text}"
        group = r.json()
        group_id = group["id"]
        invite_code = group["invite_code"]
        assert group["owner_id"] == alpha_id
        assert group["member_count"] == 1
        assert group["category"] == "ai"
        assert group["category_label_zh"] == "AI人工智能"
        ok(f"Groups: created 'AI Research' id={group_id[:8]}... invite={invite_code}")

        # ── 2. List public groups ─────────────────────────────────────────────
        r = await client.get("/api/groups")
        assert r.status_code == 200
        groups = r.json()
        assert len(groups) >= 1
        assert any(g["id"] == group_id for g in groups)
        ok(f"Groups: public list -> {len(groups)} group(s)")

        # ── 2b. List categories ────────────────────────────────────────────────
        r = await client.get("/api/groups/categories")
        assert r.status_code == 200
        cats = r.json()
        assert len(cats) >= 12
        assert any(c["value"] == "ai" and c["label_zh"] == "AI人工智能" for c in cats)
        ok(f"Groups: categories list -> {len(cats)} categories")

        # ── 2c. Filter by category ─────────────────────────────────────────────
        r = await client.get("/api/groups?category=ai")
        assert r.status_code == 200
        ai_groups = r.json()
        assert all(g["category"] == "ai" for g in ai_groups)
        ok(f"Groups: category filter 'ai' -> {len(ai_groups)} group(s)")

        # ── 3. Get group detail ───────────────────────────────────────────────
        r = await client.get(f"/api/groups/{group_id}")
        assert r.status_code == 200
        detail = r.json()
        assert detail["id"] == group_id
        assert len(detail["members"]) == 1
        assert detail["members"][0]["role"] == "admin"
        ok(f"Groups: detail -> {detail['member_count']} member(s), admin role confirmed")

        # ── 4. Beta joins via invite code ─────────────────────────────────────
        r = await client.post("/api/groups/join", json={"invite_code": invite_code}, headers=auth_b)
        assert r.status_code == 200, f"Join group: {r.text}"
        ok(f"Groups: Beta joined via invite code")

        # ── 5. Duplicate join rejected ────────────────────────────────────────
        r = await client.post("/api/groups/join", json={"invite_code": invite_code}, headers=auth_b)
        assert r.status_code == 400
        ok("Groups: duplicate join rejected (400)")

        # ── 6. Invalid invite code ────────────────────────────────────────────
        r = await client.post("/api/groups/join", json={"invite_code": "ZZZZZZ"}, headers=auth_g)
        assert r.status_code == 404
        ok("Groups: invalid invite code rejected (404)")

        # ── 7. Get group detail (2 members) ───────────────────────────────────
        r = await client.get(f"/api/groups/{group_id}")
        detail = r.json()
        assert detail["member_count"] == 2
        ok(f"Groups: member count updated -> {detail['member_count']}")

        # ── 8. My groups (Alpha should see 1) ────────────────────────────────
        r = await client.get("/api/groups/mine", headers=auth_a)
        assert r.status_code == 200
        mine = r.json()
        assert any(g["id"] == group_id for g in mine)
        ok(f"Groups: /mine returns {len(mine)} group(s) for Alpha")

        # ── 9. Update group (by admin Alpha) ──────────────────────────────────
        r = await client.put(f"/api/groups/{group_id}", json={
            "description": "Updated description"
        }, headers=auth_a)
        assert r.status_code == 200
        assert r.json()["description"] == "Updated description"
        ok("Groups: update by admin ok")

        # ── 9b. Create second group with different category ─────────────────────
        r = await client.post("/api/groups", json={
            "name": "Tech Dev Group",
            "description": "Software development group",
            "privacy": "public",
            "category": "tech",
        }, headers=auth_a)
        assert r.status_code == 201
        tech_group = r.json()
        assert tech_group["category"] == "tech"
        assert tech_group["category_label_zh"] == "技术开发"
        ok("Groups: second group created with 'tech' category")

        # ── 9c. Create private group with password ─────────────────────────────────
        r = await client.post("/api/groups", json={
            "name": "Private Club",
            "description": "A secret group",
            "privacy": "private",
            "category": "social",
            "password": "secret123",
        }, headers=auth_a)
        assert r.status_code == 201
        private_group = r.json()
        private_id = private_group["id"]
        assert private_group["privacy"] == "private"
        assert private_group["has_password"] is True
        ok(f"Groups: private group created with password, id={private_id[:8]}...")

        # ── 9d. Create private group without password -> should fail ───────────────
        r = await client.post("/api/groups", json={
            "name": "Bad Private",
            "privacy": "private",
            "category": "social",
        }, headers=auth_a)
        assert r.status_code == 400
        ok("Groups: private group without password rejected (400)")

        # ── 9e. Join private group with wrong password ───────────────────────────
        r = await client.post("/api/groups/join", json={
            "invite_code": private_group["invite_code"],
            "password": "wrongpass",
        }, headers=auth_b)
        assert r.status_code == 403
        ok("Groups: join private with wrong password rejected (403)")

        # ── 9f. Join private group with correct password ─────────────────────────
        r = await client.post("/api/groups/join", json={
            "invite_code": private_group["invite_code"],
            "password": "secret123",
        }, headers=auth_b)
        assert r.status_code == 200
        ok("Groups: join private with correct password ok")

        # ── 9g. Join private group without password ─────────────────────────────────
        r = await client.post("/api/groups/join", json={
            "invite_code": private_group["invite_code"],
        }, headers=auth_g)
        assert r.status_code == 403
        ok("Groups: join private without password rejected (403)")

        # ── 10. Non-admin update rejected ────────────────────────────────────
        r = await client.put(f"/api/groups/{group_id}", json={
            "description": "Hacked"
        }, headers=auth_b)
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
        ok("Groups: non-admin update rejected (403)")

        # ── 11. Update member role ────────────────────────────────────────────
        r = await client.put(
            f"/api/groups/{group_id}/members/{beta_id}/role",
            json={"role": "admin"},
            headers=auth_a,
        )
        assert r.status_code == 200
        assert r.json()["role"] == "admin"
        ok(f"Groups: Beta promoted to admin")

        # ── 12. Kick member (Gamma joins first, then gets kicked) ─────────────
        r = await client.post("/api/groups/join", json={"invite_code": invite_code}, headers=auth_g)
        assert r.status_code == 200
        r = await client.delete(f"/api/groups/{group_id}/members/{gamma_id}", headers=auth_a)
        assert r.status_code == 204
        ok("Groups: Gamma kicked by admin Alpha")

        # ── 13. Beta leaves group ─────────────────────────────────────────────
        r = await client.post(f"/api/groups/{group_id}/leave", headers=auth_b)
        assert r.status_code == 204
        ok("Groups: Beta left group")

        # ── 14. Owner cannot leave ────────────────────────────────────────────
        r = await client.post(f"/api/groups/{group_id}/leave", headers=auth_a)
        assert r.status_code == 400
        ok("Groups: owner leave blocked (400)")

        # ── 15. Register ability (no group) ───────────────────────────────────
        r = await client.post("/api/abilities", json={
            "name": "text_summarize",
            "definition": {
                "input": {"type": "string"},
                "output": {"type": "string"},
                "description": "Summarizes text",
            },
            "version": "1.0.0",
            "is_public": True,
            "description": "Text summarization skill",
        }, headers=auth_a)
        assert r.status_code == 201, f"Create ability: {r.text}"
        ability = r.json()
        ability_id = ability["id"]
        assert ability["name"] == "text_summarize"
        assert len(ability["hash"]) == 64  # SHA256
        ok(f"Abilities: registered 'text_summarize' id={ability_id[:8]}... hash={ability['hash'][:8]}...")

        # ── 16. Register ability in group (Beta must join first) ──────────────
        # Rejoin Beta
        r = await client.post("/api/groups/join", json={"invite_code": invite_code}, headers=auth_b)
        assert r.status_code == 200

        r = await client.post("/api/abilities", json={
            "name": "code_review",
            "group_id": group_id,
            "definition": {
                "input": {"type": "code", "language": "any"},
                "output": {"type": "review_report"},
            },
            "version": "1.0.0",
            "is_public": True,
        }, headers=auth_b)
        assert r.status_code == 201, f"Group ability: {r.text}"
        group_ability = r.json()
        assert group_ability["group_id"] == group_id
        ok(f"Abilities: Beta registered 'code_review' in group")

        # ── 17. Non-member cannot register in group ───────────────────────────
        # Gamma is not in the group (was kicked)
        r = await client.post("/api/abilities", json={
            "name": "spy_skill",
            "group_id": group_id,
            "definition": {"type": "hack"},
            "version": "1.0.0",
        }, headers=auth_g)
        assert r.status_code == 403
        ok("Abilities: non-member cannot register in group (403)")

        # ── 18. List abilities ────────────────────────────────────────────────
        r = await client.get("/api/abilities")
        assert r.status_code == 200
        abil_list = r.json()
        assert len(abil_list) >= 2
        ok(f"Abilities: list -> {len(abil_list)} abilities")

        # ── 19. List abilities by group ───────────────────────────────────────
        r = await client.get(f"/api/abilities?group_id={group_id}")
        assert r.status_code == 200
        grp_abilities = r.json()
        assert any(a["name"] == "code_review" for a in grp_abilities)
        ok(f"Abilities: filter by group -> {len(grp_abilities)} ability(ies)")

        # ── 20. My abilities ──────────────────────────────────────────────────
        r = await client.get("/api/abilities/mine", headers=auth_a)
        assert r.status_code == 200
        mine = r.json()
        assert any(a["name"] == "text_summarize" for a in mine)
        ok(f"Abilities: /mine returns {len(mine)} for Alpha")

        # ── 21. Get ability by ID ─────────────────────────────────────────────
        r = await client.get(f"/api/abilities/{ability_id}")
        assert r.status_code == 200
        assert r.json()["id"] == ability_id
        ok("Abilities: get by ID ok")

        # ── 22. Update ability ────────────────────────────────────────────────
        r = await client.put(f"/api/abilities/{ability_id}", json={
            "version": "1.1.0",
            "description": "Updated summarizer",
        }, headers=auth_a)
        assert r.status_code == 200
        updated = r.json()
        assert updated["version"] == "1.1.0"
        ok("Abilities: update version -> 1.1.0")

        # ── 22b. Downgrade version rejected ────────────────────────────────────────
        r = await client.put(f"/api/abilities/{ability_id}", json={"version": "1.0.0"}, headers=auth_a)
        assert r.status_code == 400
        ok("Abilities: downgrade version rejected (400)")

        # ── 22c. Same version rejected ─────────────────────────────────────────────
        r = await client.put(f"/api/abilities/{ability_id}", json={"version": "1.1.0"}, headers=auth_a)
        assert r.status_code == 400
        ok("Abilities: same version rejected (400)")

        # ── 23. Non-owner update rejected ────────────────────────────────────
        r = await client.put(f"/api/abilities/{ability_id}", json={"version": "9.9.9"}, headers=auth_b)
        assert r.status_code == 403
        ok("Abilities: non-owner update rejected (403)")

        # ── 24. Deprecate ability ─────────────────────────────────────────────
        r = await client.post(f"/api/abilities/{ability_id}/deprecate", headers=auth_a)
        assert r.status_code == 200
        assert r.json()["status"] == "deprecated"
        ok("Abilities: deprecate -> status=deprecated")

        # ── 25. Deprecated not in default list ───────────────────────────────
        r = await client.get("/api/abilities")
        non_deprecated = r.json()
        assert not any(a["id"] == ability_id for a in non_deprecated)
        ok("Abilities: deprecated excluded from default list")

        # ── 26. Include deprecated with flag ─────────────────────────────────
        r = await client.get("/api/abilities?include_deprecated=true")
        all_abilities = r.json()
        assert any(a["id"] == ability_id for a in all_abilities)
        ok("Abilities: include_deprecated=true shows all")

        # ── 27. Delete ability ────────────────────────────────────────────────
        r = await client.delete(f"/api/abilities/{group_ability['id']}", headers=auth_b)
        assert r.status_code == 204
        ok("Abilities: delete ok (204)")

        # ── 28. Batch register abilities ──────────────────────────────────────────
        r = await client.post("/api/abilities/batch", json={
            "abilities": [
                {"name": "batch_skill_1", "definition": {"type": "tool", "input": "text"}, "version": "1.0.0", "description": "Batch ability 1"},
                {"name": "batch_skill_2", "definition": {"type": "tool", "input": "json"}, "version": "2.0.0", "description": "Batch ability 2"},
            ]
        }, headers=auth_a)
        assert r.status_code == 201
        batch = r.json()
        assert len(batch) == 2
        names = {a["name"] for a in batch}
        assert names == {"batch_skill_1", "batch_skill_2"}
        ok(f"Abilities: batch register -> {len(batch)} abilities")

        # ── 29. Batch update existing abilities (version upgrade) ───────────────────
        r = await client.post("/api/abilities/batch", json={
            "abilities": [
                {"name": "batch_skill_1", "definition": {"type": "tool", "input": "text_v2"}, "version": "1.0.1"},
            ]
        }, headers=auth_a)
        assert r.status_code == 201
        updated_batch = r.json()
        assert updated_batch[0]["version"] == "1.0.1"
        ok("Abilities: batch update version upgrade ok")

        # ── 30. Batch rejected on version downgrade ─────────────────────────────────
        r = await client.post("/api/abilities/batch", json={
            "abilities": [
                {"name": "batch_skill_1", "definition": {"type": "tool", "input": "text_v3"}, "version": "0.9.0"},
            ]
        }, headers=auth_a)
        assert r.status_code == 201  # Returns existing, doesn't update
        assert r.json()[0]["version"] == "1.0.1"  # Still the old version
        ok("Abilities: batch skips on version downgrade (keeps existing)")

        # ── 28. Group 404 ─────────────────────────────────────────────────────
        r = await client.get("/api/groups/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404
        ok("Groups: 404 for non-existent group")

        # ── 29. Delete group (non-owner blocked) ──────────────────────────────
        r = await client.delete(f"/api/groups/{group_id}", headers=auth_b)
        assert r.status_code == 403
        ok("Groups: non-owner delete rejected (403)")

        # ── 30. Delete group (by owner) ───────────────────────────────────────
        r = await client.delete(f"/api/groups/{group_id}", headers=auth_a)
        assert r.status_code == 204
        r = await client.get(f"/api/groups/{group_id}")
        assert r.status_code == 404
        ok("Groups: owner delete ok, group gone (404)")

        # ── AI Generate Description Tests ────────────────────────────────────
        print()
        print("--- AI Generate Description ---")

        # ── 31. AI endpoint exists ───────────────────────────────────────────
        r = await client.post("/api/ai/generate-description", json={
            "name": "测试群组", "category": "ai"
        })
        assert r.status_code in [200, 503], f"AI endpoint should return 200 or 503, got {r.status_code}: {r.text}"
        if r.status_code == 200:
            data = r.json()
            assert "description" in data
            assert len(data["description"]) > 0
            ok("AI: generate description returns description")
        else:
            print(f"     [INFO] No LLM API key configured (expected in dev)")

        # ── 32. AI endpoint validates input ──────────────────────────────────
        r = await client.post("/api/ai/generate-description", json={
            "name": "", "category": "ai"
        })
        assert r.status_code == 422
        ok("AI: empty name returns 422 validation error")

        # ── 33. AI endpoint with different categories ────────────────────────
        r = await client.post("/api/ai/generate-description", json={
            "name": "量化投资研究", "category": "finance"
        })
        assert r.status_code in [200, 503]
        if r.status_code == 200:
            ok("AI: finance category generates description")
        else:
            print(f"     [INFO] No LLM API key configured")

    # ── Summary ───────────────────────────────────────────────────────────────
    passed = sum(1 for ok_, _ in results if ok_)
    total = len(results)
    print()
    print("=" * 60)
    if passed == total:
        print(f"ALL PASS: {passed}/{total} checks")
    else:
        print(f"PARTIAL: {passed}/{total} passed")
        for ok_, label in results:
            print(f"  [{'PASS' if ok_ else 'FAIL'}] {label}")
    print()
    print("P2 Coverage:")
    print("  Groups: create, list, detail, join, leave, update")
    print("  Groups: kick member, role update, owner leave blocked")
    print("  Groups: non-admin blocked, delete (owner/non-owner)")
    print("  Abilities: register (standalone + in-group)")
    print("  Abilities: list, filter, mine, get, update, deprecate")
    print("  Abilities: non-owner blocked, delete, deprecated filter")
    print("=" * 60)

    # Cleanup
    try:
        if os.path.exists("test_p2.db"):
            os.remove("test_p2.db")
    except PermissionError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
