#!/usr/bin/env python3
"""Print a source-checked MCP configuration. No installation, token reads or network calls."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skill'))
from runtime_v9.comath_adapter import MCP_BLOB, MCP_SOURCE, git_blob, operator_config

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comath-root', required=True, type=Path)
    parser.add_argument('--access', choices=['read-only','operator'], default='read-only')
    args = parser.parse_args()
    try:
        root=args.comath_root.expanduser().resolve()
        source=root/MCP_SOURCE
        if not source.is_file() or git_blob(source)!=MCP_BLOB:
            raise ValueError('MCP source differs from the audited contract; inspect/update the adapter rather than guessing compatible tools')
        entry=root/'services/comathd/dist/control/research-mcp-facade.js'
        if not entry.is_file():
            raise ValueError('Build the reviewed CoMath checkout first; the compiled operator facade is missing')
        print(operator_config(entry,args.access),end='')
        return 0
    except (OSError,ValueError) as exc:
        print(str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
