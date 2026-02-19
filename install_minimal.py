"""Install minimal dependencies to run Execution Planner Agent."""

import subprocess
import sys

# Minimal dependencies needed for Execution Planner Agent
deps = [
    "pydantic>=2.10,<3.0",
    "pydantic-settings>=2.6,<3.0",
]

print("Installing minimal dependencies for Execution Planner Agent...")
print(f"Python version: {sys.version}")

for dep in deps:
    print(f"\nInstalling {dep}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--user", dep],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print(f"✓ Successfully installed {dep}")
    else:
        print(f"✗ Failed to install {dep}")
        print(result.stderr)

print("\nDone! Try running: python run_execution_planner.py")
