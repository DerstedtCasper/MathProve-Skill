"""SymPy-based symbolic verifier."""
import argparse
import json
import sys
from sympy import sympify, simplify


def verify(expr1: str, expr2: str) -> dict:
    try:
        sym1 = sympify(expr1)
        sym2 = sympify(expr2)
        diff = simplify(sym1 - sym2)
        if diff == 0:
            return {"status": "verified", "message": "equivalent"}
        return {"status": "not_equal", "message": f"difference: {diff}"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="SymPy equivalence verifier")
    parser.add_argument("expr1", help="left expression")
    parser.add_argument("expr2", help="right expression")
    args = parser.parse_args()
    result = verify(args.expr1, args.expr2)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "verified" else 1


if __name__ == "__main__":
    sys.exit(main())
