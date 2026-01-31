from __future__ import annotations

from .constants import DEFAULT_SERVER_USER, PROD_SERVER_IP, TEST_SERVER_IP


ENVIRONMENTS: dict[str, dict[str, str]] = {
    "正式服务器": {
        "ip": PROD_SERVER_IP,
        "user": DEFAULT_SERVER_USER,
        "description": "生产环境",
    },
    "测试服务器": {
        "ip": TEST_SERVER_IP,
        "user": DEFAULT_SERVER_USER,
        "description": "测试环境（密码：KDLyx2021）",
    },
}

