TEXT_STATUS_CLEANUP_IMAGES = "\u6b63\u5728\u6e05\u7406 Docker \u955c\u50cf..."
TEXT_STATUS_CLEANUP_IMAGES_DONE = "\u955c\u50cf\u6e05\u7406\u5b8c\u6210"
TEXT_STATUS_CLEANUP_IMAGES_FAILED = "\u955c\u50cf\u6e05\u7406\u5931\u8d25"
TEXT_CLEANUP_RESULT_TITLE = "\u955c\u50cf\u6e05\u7406\u7ed3\u679c"
TEXT_ERROR_TITLE = "\u9519\u8bef"
TEXT_SHOW_CONTAINERS_REMOVED = "\u8be5\u529f\u80fd\u5df2\u79fb\u9664\uff08\u8bf7\u770b\u65e5\u5fd7\u6216\u624b\u52a8 docker \u6392\u67e5\uff09"


def _tool_mod():
    from tool.maintenance import tool as tool_mod

    return tool_mod
