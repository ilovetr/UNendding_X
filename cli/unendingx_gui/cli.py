"""unendingx-gui CLI: local web GUI for human users."""
import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

import click


def _find_npm() -> str | None:
    """Locate npm/node executable."""
    for cmd in ["npm.cmd", "npm", "npx.cmd", "npx"]:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return cmd
        except Exception:
            continue
    return None


def _check_backend(url: str) -> bool:
    """Check if backend API is reachable."""
    import urllib.request
    try:
        urllib.request.urlopen(f"{url}/health", timeout=3)
        return True
    except Exception:
        return False


def _gui_url(port: int) -> str:
    return f"http://localhost:{port}"


@click.command()
@click.option("--port", default=3000, help="Local GUI port (default: 3000)")
@click.option("--api", default="http://localhost:8000", help="Backend API URL")
@click.option("--dev", "use_dev", is_flag=True, help="Use Next.js dev server (requires npm)")
@click.option("--no-open", is_flag=True, help="Don't open browser automatically")
def gui(port: int, api: str, use_dev: bool, no_open: bool):
    """
    Start the unendingx local GUI web interface.

    Examples:

      # Open GUI in browser (frontend must be running at port 3000)
      unendingx gui

      # Start Next.js dev server automatically
      unendingx gui --dev

      # Custom ports
      unendingx gui --port 3001 --api http://localhost:9000
    """
    # 1. Check backend
    backend_ok = _check_backend(api)
    if not backend_ok:
        click.echo(
            f"\n⚠️  Backend not reachable at {api}\n"
            "  Please start the backend first:\n"
            "    unendingx server\n"
            "  Or in Docker:\n"
            "    docker compose up -d backend\n",
            err=True
        )
        if not click.confirm("Continue anyway?"):
            return

    # 2. Determine frontend root
    frontend_root = Path(__file__).resolve().parents[2] / "frontend"
    if not frontend_root.exists():
        frontend_root = Path(os.getcwd()) / "frontend"
        if not frontend_root.exists():
            click.echo(
                "Error: frontend directory not found.\n"
                "Please ensure you are running from the project root.",
                err=True
            )
            sys.exit(1)

    # 3. Start frontend if needed
    dev_process = None
    npm = _find_npm()

    if use_dev:
        if not npm:
            click.echo("Error: npm not found. Please install Node.js.", err=True)
            sys.exit(1)

        click.echo(f"Starting Next.js dev server at port {port} ...")
        env = os.environ.copy()
        env["NEXT_PUBLIC_API_URL"] = api
        env["PORT"] = str(port)
        dev_process = subprocess.Popen(
            [npm, "run", "dev"],
            cwd=str(frontend_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # Wait for dev server to be ready
        import urllib.request
        for _ in range(60):  # max 60s
            time.sleep(1)
            try:
                urllib.request.urlopen(f"http://localhost:{port}", timeout=2)
                break
            except Exception:
                continue
        else:
            click.echo("Error: Next.js dev server failed to start.", err=True)
            sys.exit(1)

        click.echo(f"Next.js dev server ready at {_gui_url(port)}")
    else:
        # Just open the browser; user should have frontend running
        click.echo(
            f"Opening GUI at {_gui_url(port)} ...\n"
            "If the page doesn't load, start the frontend first:\n"
            "  cd frontend && npm run dev\n"
            "  # then in another terminal:\n"
            "  unendingx gui\n"
        )

    # 4. Open browser
    if not no_open:
        webbrowser.open(_gui_url(port))

    # 5. Watch dev server
    if dev_process:
        click.echo("\nGUI server running. Press Ctrl+C to stop.")
        try:
            dev_process.wait()
        except KeyboardInterrupt:
            dev_process.terminate()
            click.echo("\nGUI server stopped.")
    else:
        click.echo("\nGUI opened in browser. Close it when done.")


def main():
    gui()
