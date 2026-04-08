#!/usr/bin/env python3
"""Auto-lint hook: prettier + eslint for JS files in src/.

Captures output and exits non-zero on unfixable errors so Claude can see and fix them.
"""

import json
import os
import subprocess
import sys

data = json.load(sys.stdin)
file_path = data.get("tool_input", {}).get("file_path", "")
proj = os.environ.get("CLAUDE_PROJECT_DIR", "")
src = os.path.join(proj, "src")

exit_code = 0

if file_path.startswith(src) and file_path.endswith((".js", ".jsx", ".mjs", ".cjs")):
    subprocess.run(["node_modules/.bin/prettier", "--write", file_path], cwd=proj)
    result = subprocess.run(
        ["node_modules/.bin/eslint", "--fix", file_path],
        capture_output=True,
        text=True,
        cwd=proj,
    )
    if result.returncode != 0:
        print(result.stdout, end="", file=sys.stderr)
        print(result.stderr, end="", file=sys.stderr)
        exit_code = 2  # Exit 2 feeds stderr back to Claude as an error message

sys.exit(exit_code)
