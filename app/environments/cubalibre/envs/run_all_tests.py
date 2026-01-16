import os
import subprocess
import sys

def run():
    print("🚀 RUNNING ALL TESTS (unittest discovery)...")
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    tests_dir = os.path.join(repo_root, "tests")
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", tests_dir, "-p", "test_*.py"],
        cwd=repo_root,
    )
    if result.returncode != 0:
        print("❌ Tests FAILED!")
        exit(result.returncode)
    print("\n✅ ALL TESTS PASSED.")

if __name__ == "__main__":
    run()
