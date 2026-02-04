try:
    from ._skill_proxy import proxy_module
except ImportError:  # pragma: no cover
    from _skill_proxy import proxy_module

_mod = proxy_module(__file__, globals())

if __name__ == "__main__":
    raise SystemExit(_mod.main() or 0)
