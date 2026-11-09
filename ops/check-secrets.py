#!/usr/bin/env python3
"""Current-tree high-confidence credential scan. Does not scan git history."""
import pathlib
import re
import subprocess
import sys
PATTERNS=(
 re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
 re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
 re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
 re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
 re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{45,}\b"),
 re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{30,}\b"),
)
SENSITIVE={".env","id_rsa","id_ed25519",".npmrc",".pypirc","credentials.json"}
EXT={".pem",".p12",".pfx",".key"}
def main():
    paths=subprocess.check_output(["git","ls-files","-z"]).decode().split("\0")
    issues=[]
    for pathstr in paths:
        if not pathstr:
            continue
        path=pathlib.Path(pathstr)
        if path.name in SENSITIVE or path.suffix.lower() in EXT or (
            path.name.startswith(".env.") and path.name!=".env.example"):
            issues.append((pathstr,0,"sensitive filename tracked"))
            continue
        if not path.is_file() or path.stat().st_size>2*1024*1024:
            continue
        try:
            content=path.read_text(encoding="utf-8")
        except (UnicodeError,OSError):
            continue
        for number,line in enumerate(content.splitlines(),1):
            if any(pattern.search(line) for pattern in PATTERNS):
                issues.append((pathstr,number,"potential secret"))
    for file,line,reason in issues:
        print(f"{file}:{line} {reason}",file=sys.stderr)
    if issues:
        print("Secret-pattern check failed; rotate any exposed credentials.",file=sys.stderr)
        return 1
    print("No high-confidence credentials found in current tracked text files.")
    return 0
if __name__=="__main__":
    sys.exit(main())
