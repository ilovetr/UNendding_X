#!/usr/bin/env python3
"""
川流/UnendingX 包安装脚本

使用方法:
    python install_packages.py           # 安装核心 CLI
    python install_packages.py --gui     # 同时安装 GUI
    python install_packages.py --dev     # 安装开发依赖
"""

import subprocess
import sys
import os
from pathlib import Path


def run(cmd: list[str], desc: str):
    print(f"\n{'='*50}")
    print(f"📦 {desc}")
    print(f"   Command: {' '.join(cmd)}")
    print('='*50)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        print(f"❌ Failed: {desc}")
        return False
    print(f"✅ Success: {desc}")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Install 川流/UnendingX packages")
    parser.add_argument("--gui", action="store_true", help="Also install unendingx-gui")
    parser.add_argument("--dev", action="store_true", help="Install dev dependencies")
    parser.add_argument("--editable", "-e", action="store_true", help="Install in editable mode")
    args = parser.parse_args()

    cli_dir = Path(__file__).parent.resolve()
    
    # Build pip install command
    base_cmd = [sys.executable, "-m", "pip", "install"]
    
    if args.editable:
        base_cmd.append("-e")
    
    # Install core CLI
    print(f"\n🚀 Installing from: {cli_dir}")
    
    if not run(base_cmd + [str(cli_dir)], "Installing unendingx core package"):
        sys.exit(1)
    
    # Install GUI if requested
    if args.gui:
        gui_dir = cli_dir / "unendingx_gui"
        if gui_dir.exists():
            cmd = [sys.executable, "-m", "pip", "install"]
            if args.editable:
                cmd.append("-e")
            if not run(cmd + [str(gui_dir)], "Installing unendingx-gui package"):
                sys.exit(1)
        else:
            print(f"⚠️  GUI directory not found: {gui_dir}")
    
    # Install dev dependencies if requested
    if args.dev:
        dev_cmd = [sys.executable, "-m", "pip", "install"]
        if not run(dev_cmd + ["-e", str(cli_dir) + "[dev]"], "Installing dev dependencies"):
            sys.exit(1)
    
    print("\n" + "="*50)
    print("🎉 Installation complete!")
    print("="*50)
    print("\nUsage:")
    print("  unendingx --help          # CLI help")
    print("  unendingx-gui             # Start GUI")
    print()


if __name__ == "__main__":
    main()
