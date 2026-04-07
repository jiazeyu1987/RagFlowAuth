def _tool_mod():
    from tool.maintenance import tool as tool_mod

    return tool_mod


def _delegate(app, impl_name, fallback_name, *args, **kwargs):
    impl = getattr(app, impl_name, None)
    if callable(impl):
        return impl(*args, **kwargs)

    fallback = getattr(app, fallback_name, None)
    if callable(fallback):
        return fallback(*args, **kwargs)

    try:
        from tool.maintenance.tool import RagflowAuthTool

        class_impl = getattr(RagflowAuthTool, impl_name, None)
        if callable(class_impl):
            return class_impl(app, *args, **kwargs)
    except Exception:
        pass

    raise AttributeError(f"Neither '{impl_name}' nor '{fallback_name}' is available on {type(app)!r}")
