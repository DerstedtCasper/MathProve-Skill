try:
    from ._skill_proxy import proxy_module
except ImportError:  # pragma: no cover - 兼容直接运行脚本
    from _skill_proxy import proxy_module

proxy_module(__file__, globals())
