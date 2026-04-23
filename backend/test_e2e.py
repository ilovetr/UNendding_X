"""
P1-4 End-to-End Verification
SQLite mode - no Docker/PostgreSQL required
Tests: register -> login -> A2A send -> task query
"""
import asyncio
import os
import sys

# Force UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Override DB to SQLite (no PostgreSQL needed)
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_e2e.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./test_e2e.db"
os.environ["SECRET_KEY"] = "e2e_test_secret_key_for_verification_only"

import httpx
from httpx import ASGITransport
from app.main import app
from app.database import engine, Base
from app.config import settings

assert "sqlite" in settings.DATABASE_URL, f"DB URL wrong: {settings.DATABASE_URL}"

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
    print("AgentHub P1-4 End-to-End Verification")
    print("=" * 60)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    ok("DB: tables created (SQLite)")

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:

        # 1. Health check
        r = await client.get("/health")
        assert r.status_code == 200, r.text
        ok(f"API: health check -> {r.json()['status']}")

        # 2. A2A Agent Card
        r = await client.get("/.well-known/agent.json")
        assert r.status_code == 200
        card = r.json()
        assert card["name"] == "川流/UnendingX Platform"
        ok(f"A2A: agent card name={card['name']} version={card['version']}")

        # 3. Register Agent-Alpha
        r = await client.post("/api/auth/register", json={
            "name": "Agent-Alpha",
            "endpoint": "http://agent-alpha.example.com",
        })
        assert r.status_code == 200, f"Register Alpha: {r.text}"
        alpha = r.json()
        alpha_id = alpha["id"]
        alpha_key = alpha["api_key"]
        assert alpha_key.startswith("unendingx_"), f"Key format: {alpha_key}"
        ok(f"Auth: Agent-Alpha registered id={alpha_id[:8]}... key={alpha_key[:12]}...")

        # 4. Register Agent-Beta
        r = await client.post("/api/auth/register", json={
            "name": "Agent-Beta",
            "endpoint": "http://agent-beta.example.com",
        })
        assert r.status_code == 200, f"Register Beta: {r.text}"
        beta = r.json()
        beta_id = beta["id"]
        ok(f"Auth: Agent-Beta  registered id={beta_id[:8]}...")

        # 5. Duplicate registration should fail
        r = await client.post("/api/auth/register", json={"name": "Agent-Alpha"})
        assert r.status_code == 400, "Duplicate should be 400"
        ok("Auth: duplicate registration rejected (400)")

        # 6. Login -> JWT
        r = await client.post("/api/auth/token", json={
            "id": alpha_id,
            "api_key": alpha_key,
        })
        assert r.status_code == 200, f"Login: {r.text}"
        token_data = r.json()
        alpha_jwt = token_data["access_token"]
        assert token_data["token_type"] == "bearer"
        ok(f"Auth: JWT login ok, expires_in={token_data['expires_in']}s")

        # 7. Wrong key should fail
        r = await client.post("/api/auth/token", json={
            "id": alpha_id,
            "api_key": "wrong_key_000",
        })
        assert r.status_code == 401, "Wrong key should be 401"
        ok("Auth: wrong credentials rejected (401)")

        # 8. A2A message:send
        r = await client.post("/a2a/message:send", json={
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Hello AgentHub from Agent-Alpha"}],
            },
            "sessionId": "session-test-001",
        })
        assert r.status_code == 200, f"message:send: {r.text}"
        send_result = r.json()
        task_id = send_result["taskId"]
        assert send_result["status"] == "completed"
        ok(f"A2A: message:send -> taskId={task_id[:8]}... status={send_result['status']}")

        # 9. Get task status
        r = await client.get(f"/a2a/tasks/{task_id}")
        assert r.status_code == 200, f"Get task: {r.text}"
        task_info = r.json()
        assert task_info["taskId"] == task_id
        assert task_info["status"] == "completed"
        ok(f"A2A: task query -> status={task_info['status']} msg_count={task_info['metadata']['message_count']}")

        # 10. List tasks
        r = await client.get("/a2a/tasks")
        assert r.status_code == 200
        tasks_list = r.json()
        assert len(tasks_list["tasks"]) >= 1
        ok(f"A2A: task list -> count={len(tasks_list['tasks'])}")

        # 11. message:stream (SSE)
        r = await client.post("/a2a/message:stream", json={
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "stream test"}],
            },
            "sessionId": "session-stream-001",
        })
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")
        sse_text = r.text
        assert "task_id" in sse_text or "task_update" in sse_text, f"SSE content: {sse_text[:100]}"
        ok("A2A: message:stream SSE ok")

        # 12. Delete task
        r2 = await client.post("/a2a/message:send", json={
            "message": {"role": "user", "parts": [{"type": "text", "text": "to be deleted"}]},
        })
        del_task_id = r2.json()["taskId"]
        r = await client.delete(f"/a2a/tasks/{del_task_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"
        ok("A2A: task delete ok")

        # 13. 404 on missing task
        r = await client.get("/a2a/tasks/nonexistent-task-id-xyz")
        assert r.status_code == 404
        ok("A2A: missing task returns 404")

    # Summary
    passed = sum(1 for ok_, _ in results if ok_)
    total = len(results)
    print()
    print("=" * 60)
    if passed == total:
        print(f"ALL PASS: {passed}/{total} checks")
    else:
        print(f"PARTIAL: {passed}/{total} passed")
        for ok_, label in results:
            status = "PASS" if ok_ else "FAIL"
            print(f"  [{status}] {label}")
    print()
    print("Coverage:")
    print("  DB init, health check, A2A agent card")
    print("  Agent register (x2), duplicate reject (400)")
    print("  JWT login, wrong cred reject (401)")
    print("  A2A message:send, task query, task list")
    print("  A2A message:stream (SSE), task delete, 404")
    print("=" * 60)

    # Cleanup (best-effort, Windows may lock briefly)
    try:
        if os.path.exists("test_e2e.db"):
            os.remove("test_e2e.db")
    except PermissionError:
        pass  # Will be cleaned on next run via drop_all

if __name__ == "__main__":
    asyncio.run(main())
