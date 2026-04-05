TEXT_HINT_TITLE = "\u63d0\u793a"
TEXT_RESTORE_FIXED_DIR = "\u8fd8\u539f\u9875\u7b7e\u5df2\u6539\u4e3a\u56fa\u5b9a\u76ee\u5f55\u5217\u8868\u9009\u62e9\uff1aD:\\datas\\RagflowAuth"
TEXT_RESTORE_FOLDER_NOT_EXISTS = "\u274c \u6587\u4ef6\u5939\u4e0d\u5b58\u5728"
TEXT_MISSING_AUTH_DB = "\u274c \u7f3a\u5c11 auth.db"
TEXT_FOUND_DB = "\u2705 \u627e\u5230\u6570\u636e\u5e93: {size_mb:.2f} MB"
TEXT_FOUND_IMAGES = "\u2705 \u627e\u5230 Docker \u955c\u50cf: {size_mb:.2f} MB"
TEXT_IMAGES_NOT_FOUND = "\u26a0\ufe0f  \u672a\u627e\u5230 Docker \u955c\u50cf\uff08images.tar\uff09\u2014\u4ec5\u8fd8\u539f auth.db + volumes"
TEXT_FOUND_VOLUMES = "\u2705 \u627e\u5230 RAGFlow \u6570\u636e (volumes): {count} \u4e2a\u6587\u4ef6"
TEXT_VOLUMES_NOT_FOUND = "\u2139\ufe0f  \u672a\u627e\u5230 RAGFlow \u6570\u636e (volumes)"
TEXT_LOG_PREFIX = "[RESTORE] \u5907\u4efd\u9a8c\u8bc1\u7ed3\u679c:\n"


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
