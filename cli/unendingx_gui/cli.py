"""unendingx-gui: auto-registration + local web GUI for human users."""
import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

import click

# Default to the deployed server
DEFAULT_API = "http://81.70.187.125:8000"


def _check_backend(url: str) -> bool:
    """Check if backend API is reachable."""
    import urllib.request
    try:
        urllib.request.urlopen(f"{url}/health", timeout=3)
        return True
    except Exception:
        return False


def _check_registered() -> tuple[bool, dict]:
    """Check if agent is already registered."""
    from unendingx.config import load_config
    config = load_config()
    if config.get("access_token") and config.get("agent_id"):
        return True, config
    return False, {}


def _auto_register(api_url: str) -> dict:
    """Auto-register agent and return credentials."""
    from unendingx.client import APIClient
    from unendingx.config import save_auth
    import uuid

    client = APIClient(api_url)
    device_id = str(uuid.getnode())  # Hardware ID as device_id

    # Generate a friendly name
    import socket
    hostname = socket.gethostname()
    agent_name = f"{hostname}-gui"

    r = client.post("/api/auth/init", {"name": agent_name, "device_id": device_id})
    d = r.json()

    save_auth(
        agent_id=d["agent_id"],
        name=d["name"],
        access_token=d["access_token"],
        refresh_token=d["refresh_token"],
        expires_in=d["expires_in"],
        base_url=api_url,
    )
    return d


def _find_npm() -> str | None:
    """Locate npm/node executable."""
    for cmd in ["npm.cmd", "npm", "npx.cmd", "npx"]:
        try:
            result = subprocess.run(
                [cmd, "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return cmd
        except Exception:
            continue
    return None


def _start_frontend(frontend_root: Path, port: int, api_url: str):
    """Start Next.js dev server and wait for it to be ready."""
    npm = _find_npm()
    if not npm:
        click.echo("Error: npm not found. Please install Node.js.", err=True)
        sys.exit(1)

    click.echo(f"Starting frontend at port {port} ...")
    env = os.environ.copy()
    env["NEXT_PUBLIC_API_URL"] = api_url
    env["PORT"] = str(port)

    proc = subprocess.Popen(
        [npm, "run", "dev"],
        cwd=str(frontend_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Wait for server ready (max 60s)
    import urllib.request
    for _ in range(60):
        time.sleep(1)
        try:
            urllib.request.urlopen(f"http://localhost:{port}", timeout=2)
            click.echo(f"Frontend ready at http://localhost:{port}")
            return proc
        except Exception:
            continue

    click.echo("Error: Frontend failed to start.", err=True)
    sys.exit(1)


def _gui_url(port: int) -> str:
    return f"http://localhost:{port}"


@click.command()
@click.option("--port", default=3000, help="Local GUI port (default: 3000)")
@click.option("--api", default=DEFAULT_API, help="Backend API URL")
@click.option("--no-open", is_flag=True, help="Don't open browser automatically")
def gui(port: int, api: str, no_open: bool):
    """
    Start 川流/UnendingX GUI.

    Installation auto-registers this device with the 川流 platform.
    Run without arguments to open the GUI.
    """
    # 1. Check / auto-register
    click.echo("川流/UnendingX GUI")
    registered, config = _check_registered()

    if not registered:
        click.echo(f"\nAuto-registering with {api} ...")
        try:
            d = _auto_register(api)
            click.echo(f"✅ Registered as: {d['name']} (ID: {d['agent_id'][:8]}...)")
        except Exception as e:
            click.echo(f"⚠️  Registration failed: {e}", err=True)
            click.echo("Will continue anyway...")
    else:
        click.echo(f"✅ Already registered as: {config.get('name', 'unknown')}")

    # 2. Check backend connectivity
    backend_ok = _check_backend(api)
    if not backend_ok:
        click.echo(f"\n⚠️  Backend not reachable at {api}", err=True)
        click.echo("Please check your network or server address.")
        if not click.confirm("Continue anyway?"):
            return

    # 3. Find frontend
    frontend_root = Path(__file__).resolve().parents[2] / "frontend"
    if not frontend_root.exists():
        frontend_root = Path(os.getcwd()) / "frontend"
    if not frontend_root.exists():
        click.echo("Error: frontend directory not found.", err=True)
        sys.exit(1)

    # 4. Check if frontend already running
    import urllib.request
    frontend_running = False
    try:
        urllib.request.urlopen(f"http://localhost:{port}", timeout=2)
        frontend_running = True
        click.echo(f"Using existing frontend at port {port}")
    except Exception:
        pass

    # 5. Start frontend if not running
    dev_proc = None
    if not frontend_running:
        dev_proc = _start_frontend(frontend_root, port, api)

    # 6. Open browser
    url = _gui_url(port)
    if not no_open:
        click.echo(f"\nOpening GUI at {url} ...")
        webbrowser.open(url)
    else:
        click.echo(f"\nGUI available at {url}")

    # 7. Keep running
    click.echo("\nPress Ctrl+C to stop.")
    try:
        if dev_proc:
            dev_proc.wait()
        else:
            # Just keep alive - user will close browser when done
            while True:
                time.sleep(10)
    except KeyboardInterrupt:
        if dev_proc:
            dev_proc.terminate()
        click.echo("\nGUI stopped.")


def main():
    gui()