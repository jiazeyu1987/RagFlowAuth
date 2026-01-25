import logging

from fastapi import APIRouter, Response as FastAPIResponse

from backend.app.core.authz import AuthContextDep
from backend.app.core.datasets import list_accessible_datasets
from backend.app.core.permdbg import permdbg

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/datasets")
async def list_datasets(
    ctx: AuthContextDep,
    response: FastAPIResponse,
):
    """
    列出RAGFlow数据集（基于权限组过滤）

    权限规则：
    - 管理员：可以看到所有数据集
    - 其他角色：根据权限组的accessible_kbs配置
    """
    deps = ctx.deps
    snapshot = ctx.snapshot

    # Compatibility: legacy endpoint. Prefer `/api/datasets`.
    response.headers["Deprecation"] = "true"
    response.headers["X-Replaced-By"] = "/api/datasets"

    datasets = list_accessible_datasets(deps, snapshot)
    filtered = datasets
    try:
        permdbg(
            "ragflow.datasets.deprecated",
            user=ctx.user.username,
            role=ctx.user.role,
            kb_scope=snapshot.kb_scope,
            kb_refs=sorted(list(snapshot.kb_names))[:50],
            datasets=[d.get("name") for d in filtered[:50] if isinstance(d, dict)],
        )
    except Exception:
        pass
    return {"datasets": filtered}

