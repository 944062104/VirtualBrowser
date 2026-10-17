"""Cross-Platform Self-Check & Smoke Test for VirtualBrowser api_server
======================================================================
Validates path resolution, process control with psutil, and port allocation.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add parent directory to sys.path so we can import core directly
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import core
import psutil


def test_vb_base_dir():
    base_dir = core.get_vb_base_dir()
    assert isinstance(base_dir, Path), "get_vb_base_dir should return a Path instance"
    print(f"[OK] get_vb_base_dir resolved to: {base_dir}")
    assert core.VB_USER_DATA_DIR == base_dir / "User Data"
    assert core.VB_WORKERS_DIR == base_dir / "Workers"


def test_free_port():
    port = core.find_free_port(9222, 9300)
    assert 9222 <= port <= 9300, f"Port {port} out of range"
    print(f"[OK] find_free_port found port: {port}")


def test_kill_process_tree():
    # 1. Non-existent PID should not raise error
    core.kill_process_tree(99999999)
    print("[OK] kill_process_tree safely handled nonexistent PID")

    # 2. Real spawned sub-process tree
    sub = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
    assert sub.poll() is None, "Subprocess should be running"
    pid = sub.pid
    core.kill_process_tree(pid)
    time.sleep(0.5)
    assert not psutil.pid_exists(pid) or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE, "Process should be killed"
    print(f"[OK] kill_process_tree successfully killed test process {pid}")


def test_browser_executable():
    try:
        exe = core.find_browser_executable()
        print(f"[OK] find_browser_executable found: {exe}")
        assert exe.exists()
    except FileNotFoundError as e:
        print(f"[INFO] Chromium executable not found in default paths: {e}")


def test_cleanup_profile_locks():
    core.cleanup_profile_locks("test_worker_999")
    print("[OK] cleanup_profile_locks ran without exception")


def main():
    print("=" * 60)
    print("  Running VirtualBrowser Cross-Platform Smoke Tests")
    print(f"  Platform: {sys.platform} | Python: {sys.version.split()[0]}")
    print("=" * 60)

    test_vb_base_dir()
    test_free_port()
    test_kill_process_tree()
    test_browser_executable()
    test_cleanup_profile_locks()

    print("=" * 60)
    print("  🎉 All cross-platform smoke tests passed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
