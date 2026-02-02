# SymPy 执行模板（由 verify_sympy.py 注入并运行）
import json

from sympy import *  # noqa: F401,F403


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False))
