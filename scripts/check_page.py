"""Syntax-check the inline scripts of a built page with `node --check` (skips quietly if node is absent).

    python check_page.py <folder>/index.html
"""
import re, shutil, subprocess, sys, tempfile
from pathlib import Path

page = Path(sys.argv[1])
html = page.read_text(encoding="utf-8")
js = "\n".join(re.findall(r"<script>(.*?)</script>", html, re.S))
if not shutil.which("node"):
    print("node not found: skipped the syntax check")
    sys.exit(0)
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
    f.write(js)
r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
Path(f.name).unlink(missing_ok=True)
if r.returncode:
    print(r.stderr)
    sys.exit(1)
print(f"{page.name}: scripts parse OK")
