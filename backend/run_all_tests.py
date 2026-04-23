#!/usr/bin/env python3
"""
AgentHub 综合测试运行器
运行所有 e2e 测试并输出汇总报告

用法:
    python run_all_tests.py          # 运行全部
    python run_all_tests.py --p1     # 只运行 P1
    python run_all_tests.py --p2     # 只运行 P2
    python run_all_tests.py --p3     # 只运行 P3
    python run_all_tests.py --cli    # 只运行 CLI e2e
"""
import subprocess
import sys
import os
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 项目根目录（backend/）
SCRIPT_DIR = Path(__file__).parent.absolute()
os.chdir(SCRIPT_DIR)

# 确保 backend 目录
if not (SCRIPT_DIR / "app").exists():
    os.chdir(SCRIPT_DIR.parent)

BACKEND_DIR = Path.cwd()

@dataclass
class TestResult:
    name: str
    passed: int
    total: int
    duration: float
    output: str
    success: bool


def run_test(script_name: str, description: str) -> TestResult:
    """运行单个测试脚本并捕获结果。"""
    import time
    start = time.time()

    script_path = BACKEND_DIR / script_name
    if not script_path.exists():
        return TestResult(
            name=description,
            passed=0, total=0,
            duration=time.time() - start,
            output=f"[ERROR] Script not found: {script_path}",
            success=False,
        )

    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite+aiosqlite:///./test_p5.db"
    env["DATABASE_URL_SYNC"] = "sqlite:///./test_p5.db"
    env["SECRET_KEY"] = "p5_verification_secret_key"
    env["AGENT_ENDPOINT"] = "http://localhost:8000"

    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
            cwd=str(BACKEND_DIR),
        )
        output = proc.stdout + "\n" + proc.stderr

        # 解析通过数量
        passed, total = 0, 0
        for line in output.splitlines():
            stripped = line.strip()
            if "Results:" in stripped and "/" in stripped:
                # e.g. "Results: 17/17 passed"
                try:
                    parts = stripped.split("/")
                    total = int(parts[1].split()[0])
                    passed = int(parts[0].split()[-1])
                except (IndexError, ValueError):
                    pass
            elif "ALL PASS:" in stripped:
                # e.g. "ALL PASS: 32/32 checks" or "ALL PASS: 20/20"
                try:
                    right = stripped.split(":")[-1].strip().split("/")
                    total = int(right[1].split()[0])
                    passed = int(right[0].strip())
                except (IndexError, ValueError):
                    pass

        duration = time.time() - start
        success = proc.returncode == 0 and passed == total and total > 0

        return TestResult(
            name=description,
            passed=passed,
            total=total,
            duration=duration,
            output=output,
            success=success,
        )

    except subprocess.TimeoutExpired:
        return TestResult(
            name=description,
            passed=0, total=0,
            duration=time.time() - start,
            output="[TIMEOUT] Test exceeded 120 seconds",
            success=False,
        )
    except Exception as e:
        return TestResult(
            name=description,
            passed=0, total=0,
            duration=time.time() - start,
            output=f"[ERROR] {e}",
            success=False,
        )


def print_result(r: TestResult):
    status = "[PASS]" if r.success else "[FAIL]"
    bar = "▓" * r.passed + "░" * (r.total - r.passed) if r.total > 0 else ""
    print(f"  {status} {r.name}")
    if r.total > 0:
        print(f"       {r.passed}/{r.total}  ({r.duration:.1f}s)  {bar}")
    if not r.success and r.output:
        lines = r.output.strip().splitlines()
        # 只显示最后 10 行错误
        for line in lines[-10:]:
            print(f"       > {line}")


def print_summary(results: List[TestResult]):
    total_passed = sum(r.passed for r in results)
    total_all = sum(r.total for r in results)
    total_duration = sum(r.duration for r in results)
    all_pass = all(r.success for r in results)

    print("\n" + "=" * 60)
    print(f"  {'综合测试汇总':^30}  ")
    print("=" * 60)
    print(f"  总计:  {total_passed}/{total_all}  ({total_duration:.1f}s)")
    print()

    for r in results:
        icon = "[PASS]" if r.success else "[FAIL]"
        print(f"  {icon}  {r.name:<30} {r.passed:>4}/{r.total:<4}  {r.duration:>5.1f}s")

    print()
    if all_pass:
        print(f"  [ALL PASS] {len(results)}/{len(results)} suites")
    else:
        failed = [r.name for r in results if not r.success]
        print(f"  [FAIL] Failed: {', '.join(failed)}")
    print("=" * 60)

    # 清理测试数据库
    db_file = BACKEND_DIR / "test_p5.db"
    if db_file.exists():
        try:
            os.remove(db_file)
        except Exception:
            pass

    return all_pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AgentHub 综合测试")
    parser.add_argument("--p1", action="store_true", help="只运行 P1 (test_e2e.py)")
    parser.add_argument("--p2", action="store_true", help="只运行 P2 (test_p2.py)")
    parser.add_argument("--p3", action="store_true", help="只运行 P3 (test_p3.py)")
    parser.add_argument("--cli", action="store_true", help="只运行 CLI (test_cli_e2e.py)")
    parser.add_argument("--all", action="store_true", help="运行全部测试")
    args = parser.parse_args()

    # 默认运行全部
    run_all = args.all or not any([args.p1, args.p2, args.p3, args.cli])

    print("╔══════════════════════════════════════════════════╗")
    print("║         AgentHub 综合测试运行器  v0.1.0           ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"  Backend: {BACKEND_DIR}")
    print(f"  Python:  {sys.version.split()[0]}")
    print(f"  Mode:    {'全部' if run_all else '单项'}")
    print()

    results: List[TestResult] = []

    if run_all or args.cli:
        print("━━━ CLI 端到端 (17步) ━━━━━━━━━━━━━━━━━━━━━━")
        results.append(run_test("test_cli_e2e.py", "CLI 端到端"))

    if run_all or args.p1:
        print("\n━━━ P1: 认证 + A2A (14/14) ━━━━━━━━━━━━━━━━━━")
        results.append(run_test("test_e2e.py", "P1: 认证 + A2A"))

    if run_all or args.p2:
        print("\n━━━ P2: 群组 + 能力 (32/32) ━━━━━━━━━━━━━━━━")
        results.append(run_test("test_p2.py", "P2: 群组 + 能力"))

    if run_all or args.p3:
        print("\n━━━ P3: 权限 + SKILL 令牌 (20/20) ━━━━━━━━━━")
        results.append(run_test("test_p3.py", "P3: 权限 + SKILL"))

    # 打印所有结果
    print("\n━━━ 测试结果详情 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for r in results:
        print_result(r)

    success = print_summary(results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
