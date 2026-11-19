#!/usr/bin/env python3
"""Generate the Ren'Py profile fingerprint table from official SDK bundles."""
import hashlib
from pathlib import Path
import re
import sys

SCRIPTS = ("000statements", "000atl", "00action_control", "00action_other", "00keymap", "00start", "00preferences")

for argument in sys.argv[1:]:
    directory = Path(argument)
    match = re.fullmatch(r"renpy-(\d+\.\d+)\.\d+-sdk", directory.name)
    if not match:
        raise SystemExit("Expected an official Ren'Py SDK directory with its original name.")
    print('        new Profile("' + match[1] + '",')
    for index, script in enumerate(SCRIPTS):
        data = (directory / "renpy" / "common" / (script + ".rpyc")).read_bytes()
        assert data.startswith(b"RENPY RPC2") and len(data) > 16
        suffix = "," if index < len(SCRIPTS) - 1 else "),"
        print('            "' + hashlib.sha256(data).hexdigest() + ':' + data[-16:].hex() + '"' + suffix)
