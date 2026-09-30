#!/usr/bin/env python3
"""Print MCP configuration for an existing entry; no source pins or network calls."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skill'))
from runtime_v9.comath_adapter import operator_config

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comath-root', required=True, type=Path)
    parser.add_argument('--access', choices=['read-only','operator'], default='read-only')
    args = parser.parse_args()
    try:
        root=args.comath_root.expanduser().resolve()
        entry=root/'services/comathd/dist/control/research-mcp-facade.js'
        if not entry.is_file():
            raise ValueError('Build the current CoMath checkout first; the compiled MCP entry is missing')
        print(operator_config(entry,args.access),end='')
        return 0
    except (OSError,ValueError) as exc:
        print(str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
