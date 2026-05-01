"""川流/UnendingX CLI - Main command-line interface."""

import json
import os
import sys
import subprocess

import click

from unendingx.client import APIClient
from unendingx.config import load_config, save_config, save_auth, is_token_expired, update_access_token, _get_device_id
from unendingx.format import print_error, print_json, print_success, print_table

BASE_URL = os.environ.get("UNENDINGX_URL", "http://localhost:8000")


def _auto_register(base_url: str) -> dict | None:
    """Auto-register this agent. Returns registration data or None on failure."""
    import socket
    try:
        client = APIClient(base_url)
        device_id = _get_device_id()
        hostname = socket.gethostname()
        name = f"{hostname}-cli"
        r = client.post("/api/auth/init", {"name": name, "device_id": device_id})
        d = r.json()
        save_auth(
            agent_id=d["agent_id"],
            name=d["name"],
            access_token=d["access_token"],
            refresh_token=d["refresh_token"],
            expires_in=d["expires_in"],
            base_url=base_url,
        )
        return d
    except Exception as e:
        return None


@click.group()
@click.option("--url", default=BASE_URL, help="API base URL")
@click.pass_context
def cli(ctx, url):
    """川流/UnendingX CLI - Manage agents, groups, abilities, and skills."""
    ctx.ensure_object(dict)
    config = load_config()
    ctx.obj["config"] = config
    ctx.obj["url"] = url
    ctx.obj["client"] = APIClient(url)

    # Auto-register if not logged in (first run)
    if not config.get("access_token") or is_token_expired():
        click.echo("\n🔄 First run detected. Auto-registering this agent...")
        d = _auto_register(url)
        if d:
            click.echo(f"✅ Registered as: {d['name']} (ID: {d['agent_id'][:8]}...)")
        else:
            click.echo("⚠️  Auto-registration failed. Some commands may not work.", err=True)


@cli.group("auth")
def auth_group():
    """Authentication commands."""


@auth_group.command("register")
@click.option("--name", required=True, help="Agent name")
@click.option("--did", default=None, help="DID URL")
@click.option("--endpoint", default=None, help="Agent endpoint URL")
@click.pass_context
def register(ctx, name, did, endpoint):
    """Register a new agent."""
    data = {"name": name}
    if did:
        data["did"] = did
    if endpoint:
        data["endpoint"] = endpoint
    r = ctx.obj["client"].post("/api/auth/register", data)
    d = r.json()
    print_success(f"Registered! Agent ID: {d['id']}")
    click.echo(f"API Key (save this!): {d['api_key']}")
    # Auto-login
    config = ctx.obj["config"]
    config["base_url"] = ctx.obj["url"]
    config["agent_id"] = d["id"]
    # Login to get JWT
    r2 = ctx.obj["client"].post("/api/auth/token", {"id": d["id"], "api_key": d["api_key"]})
    config["access_token"] = r2.json()["access_token"]
    save_config(config)
    print_success("Auto-logged in. Token saved to config.")


@auth_group.command("login")
@click.option("--id", "agent_id", required=True, help="Agent ID")
@click.option("--api-key", required=True, help="API Key")
@click.pass_context
def login(ctx, agent_id, api_key):
    """Login with agent ID and API key."""
    r = ctx.obj["client"].post("/api/auth/token", {"id": agent_id, "api_key": api_key})
    config = ctx.obj["config"]
    config["base_url"] = ctx.obj["url"]
    config["agent_id"] = agent_id
    config["access_token"] = r.json()["access_token"]
    save_config(config)
    print_success("Logged in successfully!")


@auth_group.command("status")
@click.pass_context
def status(ctx):
    """Show current auth status."""
    config = ctx.obj["config"]
    if config.get("access_token"):
        import time
        expires_at = config.get("token_expires_at", 0)
        remaining = max(0, int(expires_at - time.time()))
        
        print_success(f"Logged in as: {config.get('name', 'unknown')}")
        click.echo(f"Agent ID: {config.get('agent_id', 'unknown')}")
        click.echo(f"Base URL: {config.get('base_url', 'unknown')}")
        click.echo(f"Token expires in: {remaining // 60} minutes")
        if config.get("refresh_token"):
            click.echo(f"Refresh Token: ✅ Saved")
        else:
            click.echo(f"Refresh Token: ❌ Not found")
    else:
        print_error("Not logged in. Run any unendingx command to auto-register, or use 'unendingx auth login'.")


@auth_group.command("logout")
@click.pass_context
def logout(ctx):
    """Clear stored credentials."""
    config = ctx.obj["config"]
    config.pop("agent_id", None)
    config.pop("name", None)
    config.pop("access_token", None)
    config.pop("refresh_token", None)
    config.pop("token_expires_at", None)
    save_config(config)
    print_success("Logged out. All credentials cleared.")


# ─── GROUPS ───────────────────────────────────────────────────────────────────


@cli.group("groups")
def groups_group():
    """Group management."""


@groups_group.command("list")
@click.pass_context
def groups_list(ctx):
    """List public groups."""
    r = ctx.obj["client"].get("/api/groups", token=ctx.obj["config"].get("access_token"))
    groups = r.json()
    if not groups:
        click.echo("No public groups found.")
        return
    print_table(
        ["ID", "Name", "Description", "Members"],
        [[g["id"][:8], g["name"], g.get("description", ""), g.get("member_count", 0)] for g in groups],
        title="Public Groups",
    )


@groups_group.command("mine")
@click.pass_context
def groups_mine(ctx):
    """List groups I belong to."""
    r = ctx.obj["client"].get("/api/groups/mine", token=ctx.obj["config"].get("access_token"))
    groups = r.json()
    if not groups:
        click.echo("You don't belong to any groups.")
        return
    print_table(
        ["ID", "Name", "Privacy", "Members"],
        [[g["id"][:8], g["name"], g.get("privacy", ""), g.get("member_count", 0)] for g in groups],
        title="My Groups",
    )


@groups_group.command("create")
@click.option("--name", required=True)
@click.option("--description", default="")
@click.option("--privacy", type=click.Choice(["public", "private"]), default="public", help="Group privacy setting")
@click.pass_context
def groups_create(ctx, name, description, privacy):
    """Create a new group."""
    data = {"name": name, "description": description, "privacy": privacy}
    r = ctx.obj["client"].post("/api/groups", data, token=ctx.obj["config"].get("access_token"))
    g = r.json()
    print_success(f"Group created: {g['name']}")
    click.echo(f"ID: {g['id']}")
    click.echo(f"Invite Code: {g.get('invite_code', 'N/A')}")


@groups_group.command("join")
@click.option("--code", required=True, help="Invite code")
@click.option("--password", default=None, help="Password for private groups")
@click.pass_context
def groups_join(ctx, code, password):
    """Join a group by invite code (use --password for private groups)."""
    payload = {"invite_code": code}
    if password:
        payload["password"] = password
    r = ctx.obj["client"].post("/api/groups/join", payload, token=ctx.obj["config"].get("access_token"))
    g = r.json()
    print_success(f"Joined group: {g['name']} (ID: {g['id'][:8]})")


@groups_group.command("leave")
@click.argument("group_id")
@click.pass_context
def groups_leave(ctx, group_id):
    """Leave a group."""
    r = ctx.obj["client"].post(f"/api/groups/{group_id}/leave", token=ctx.obj["config"].get("access_token"))
    print_success(f"Left group: {group_id[:8]}")


@groups_group.command("send")
@click.option("--group-id", required=True, help="Group ID")
@click.option("--content", required=True, help="Message content")
@click.option("--mentions", default="", help="Comma-separated agent IDs to mention")
@click.pass_context
def groups_send(ctx, group_id, content, mentions):
    """Send a message to a group."""
    sender = {
        "type": "agent",
        "id": ctx.obj["config"].get("agent_id"),
        "name": ctx.obj["config"].get("name", "CLI Agent"),
    }
    data = {
        "sender": sender,
        "content": content,
        "mentions": [m.strip() for m in mentions.split(",") if m.strip()] if mentions else [],
    }
    r = ctx.obj["client"].post(
        f"/api/groups/{group_id}/messages",
        data,
        token=ctx.obj["config"].get("access_token"),
    )
    msg = r.json()
    print_success(f"Message sent to group {group_id[:8]}")
    click.echo(f"Message ID: {msg['id']}")


@groups_group.command("history")
@click.option("--group-id", required=True, help="Group ID")
@click.option("--limit", default=20, help="Number of messages to fetch")
@click.pass_context
def groups_history(ctx, group_id, limit):
    """View message history for a group."""
    r = ctx.obj["client"].get(
        f"/api/groups/{group_id}/messages",
        token=ctx.obj["config"].get("access_token"),
    )
    messages = r.json()
    if not messages:
        click.echo("No messages found.")
        return
    # Show most recent first, limited to --limit
    for msg in messages[:limit]:
        sender = msg.get("sender", {})
        click.echo(f"[{msg['timestamp'][:19]}] {sender.get('name', 'Unknown')}: {msg['content'][:80]}")


@groups_group.command("members")
@click.option("--group-id", required=True, help="Group ID")
@click.pass_context
def groups_members(ctx, group_id):
    """List members of a group."""
    r = ctx.obj["client"].get(
        f"/api/groups/{group_id}",
        token=ctx.obj["config"].get("access_token"),
    )
    group = r.json()
    members = group.get("members", [])
    if not members:
        click.echo("No members found.")
        return
    print_table(
        ["Agent ID", "Name", "Role", "Joined"],
        [[m["agent_id"][:8], m["agent_name"], m["role"], m["joined_at"][:10]] for m in members],
        title=f"Members of {group.get('name', group_id[:8])}",
    )


# ─── ABILITIES ────────────────────────────────────────────────────────────────


@cli.group("abilities")
def abilities_group():
    """Ability management."""


@abilities_group.command("list")
@click.option("--group", "group_id", default=None, help="Filter by group ID")
@click.pass_context
def abilities_list(ctx, group_id):
    """List abilities."""
    path = "/api/abilities"
    if group_id:
        path += f"?group_id={group_id}"
    r = ctx.obj["client"].get(path, token=ctx.obj["config"].get("access_token"))
    abilities = r.json()
    if not abilities:
        click.echo("No abilities found.")
        return
    print_table(
        ["ID", "Name", "Version", "Status"],
        [[a["id"][:8], a["name"], a["version"], a.get("status", "")] for a in abilities],
        title="Abilities",
    )


@abilities_group.command("mine")
@click.pass_context
def abilities_mine(ctx):
    """List my abilities."""
    r = ctx.obj["client"].get("/api/abilities/mine", token=ctx.obj["config"].get("access_token"))
    abilities = r.json()
    if not abilities:
        click.echo("You haven't registered any abilities.")
        return
    print_table(
        ["ID", "Name", "Version", "Status"],
        [[a["id"][:8], a["name"], a["version"], a.get("status", "")] for a in abilities],
        title="My Abilities",
    )


@abilities_group.command("register")
@click.option("--name", required=True)
@click.option("--description", default="")
@click.option("--version", default="1.0.0")
@click.option("--definition", default='{"input":"text","output":"result"}', help="JSON definition object")
@click.option("--group", "group_id", default=None)
@click.pass_context
def abilities_register(ctx, name, description, version, definition, group_id):
    """Register a new ability."""
    data = {
        "name": name,
        "description": description,
        "version": version,
        "definition": json.loads(definition),
    }
    if group_id:
        data["group_id"] = group_id
    r = ctx.obj["client"].post("/api/abilities", data, token=ctx.obj["config"].get("access_token"))
    a = r.json()
    print_success(f"Ability registered: {a['name']} v{a['version']} (ID: {a['id'][:8]})")


# ─── SKILLS ───────────────────────────────────────────────────────────────────


@cli.group("skills")
def skills_group():
    """SKILL token management."""


@skills_group.command("install")
@click.option("--skill-name", required=True)
@click.option("--version", default="1.0.0")
@click.option("--ability", "ability_ids", multiple=True, help="Ability IDs to grant")
@click.option("--group", "group_id", default=None)
@click.pass_context
def skills_install(ctx, skill_name, version, ability_ids, group_id):
    """Install a skill and get a SKILL token."""
    data = {"skill_name": skill_name, "version": version}
    if ability_ids:
        data["ability_ids"] = list(ability_ids)
    if group_id:
        data["group_id"] = group_id
    r = ctx.obj["client"].post("/api/skills/install", data, token=ctx.obj["config"].get("access_token"))
    d = r.json()
    print_success(f"SKILL token installed: {d['skill_name']}")
    click.echo(f"Token ID: {d['token_id'][:8]}...")
    click.echo(f"Permissions: {d['permissions']}")
    click.echo(f"Expires: {d['expires_at']}")
    click.echo(f"\nToken:\n{d['token'][:60]}...")


@skills_group.command("verify")
@click.option("--token", required=True)
@click.pass_context
def skills_verify(ctx, token):
    """Verify a SKILL token."""
    r = ctx.obj["client"].post("/api/skills/verify", {"token": token})
    d = r.json()
    if d["valid"]:
        print_success("Token is VALID")
        click.echo(f"Skill: {d.get('skill_name', '')}")
        click.echo(f"Agent: {d.get('agent_id', '')}")
        click.echo(f"Expires: {d.get('expires_at', '')}")
    else:
        print_error(f"Token INVALID (revoked={d.get('revoked')})")


@skills_group.command("check")
@click.option("--token", required=True)
@click.option("--ability-id", required=True)
@click.pass_context
def skills_check(ctx, token, ability_id):
    """Check if a SKILL token has a specific ability permission."""
    r = ctx.obj["client"].post("/api/skills/check", {"token": token, "ability_id": ability_id})
    d = r.json()
    if d["allowed"]:
        print_success("ALLOWED - token has this permission")
    else:
        print_error(f"DENIED: {d.get('reason', 'unknown')}")


@skills_group.command("list")
@click.pass_context
def skills_list(ctx):
    """List my SKILL tokens."""
    r = ctx.obj["client"].get("/api/skills/my-tokens", token=ctx.obj["config"].get("access_token"))
    tokens = r.json()
    if not tokens:
        click.echo("No SKILL tokens.")
        return
    print_table(
        ["ID", "Skill", "Version", "Permissions", "Expires"],
        [[t["id"][:8], t["skill_name"], t["version"], len(t.get("permissions", [])), t["expires_at"][:16]] for t in tokens],
        title="My SKILL Tokens",
    )


@skills_group.command("revoke")
@click.argument("token_id")
@click.pass_context
def skills_revoke(ctx, token_id):
    """Revoke a SKILL token."""
    r = ctx.obj["client"].delete(f"/api/skills/{token_id}", token=ctx.obj["config"].get("access_token"))
    if r.status_code == 204:
        print_success(f"Token revoked: {token_id[:8]}")
    else:
        print_error(f"Failed: {r.status_code} - {r.text}")


# ─── AUDIT ────────────────────────────────────────────────────────────────────


@cli.group("audit")
def audit_group():
    """Audit log viewer."""


@audit_group.command("list")
@click.option("--action", default=None)
@click.option("--limit", default=50, type=int)
@click.pass_context
def audit_list(ctx, action, limit):
    """List audit logs."""
    url = f"/api/audit?limit={limit}"
    if action:
        url += f"&action={action}"
    r = ctx.obj["client"].get(url, token=ctx.obj["config"].get("access_token"))
    logs = r.json()
    if not logs:
        click.echo("No audit logs.")
        return
    print_table(
        ["Timestamp", "Action", "Agent", "Details"],
        [[l["timestamp"][:16], l["action"], l.get("agent_id", "")[:8], str(l.get("details", ""))[:40]] for l in logs],
        title=f"Audit Logs (showing {len(logs)})",
    )


# ─── A2A ──────────────────────────────────────────────────────────────────────


@cli.group("a2a")
def a2a_group():
    """A2A protocol commands."""


@a2a_group.command("message")
@click.option("--text", required=True, help="Message text")
@click.pass_context
def a2a_message(ctx, text):
    """Send an A2A message."""
    data = {
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": text}],
        },
    }
    r = ctx.obj["client"].post("/a2a/message:send", data, token=ctx.obj["config"].get("access_token"))
    d = r.json()
    task_id = d.get("taskId", d.get("task_id", ""))
    print_success(f"Message sent! Task ID: {task_id[:8] if task_id else 'N/A'}")
    print_json(d)


# ─── INFO ─────────────────────────────────────────────────────────────────────


@cli.command("info")
@click.pass_context
def info(ctx):
    """Show agent info and API status."""
    try:
        r = ctx.obj["client"].get("/health")
        print_success("Backend: Online")
        print_json(r.json())
    except Exception as e:
        print_error(f"Backend unreachable: {e}")


# ─── SERVER ───────────────────────────────────────────────────────────────────


@cli.command("server")
@click.option("--host", default="0.0.0.0", help="Host to bind")
@click.option("--port", default=8000, type=int, help="Port to bind")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def server(host, port, reload):
    """Start the unendingx backend API server."""
    backend_dir = _find_backend_dir()
    if not backend_dir:
        print_error(
            "Backend directory not found.\n"
            "Please ensure you are running from the project root,\n"
            "or that the backend/ directory exists."
        )
        sys.exit(1)

    env = os.environ.copy()
    db_url = env.get("DATABASE_URL", "")
    if not db_url:
        # Default to SQLite dev mode
        env["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
        env["DATABASE_URL_SYNC"] = "sqlite:///./test.db"
        env["SECRET_KEY"] = env.get("SECRET_KEY", "dev_key_change_in_production")

    click.echo(f"Starting unendingx backend at http://{host}:{port}")
    click.echo(f"Backend dir: {backend_dir}")

    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", str(host), "--port", str(port),
             *(["--reload"] if reload else [])],
            cwd=backend_dir,
            env=env,
        )
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
