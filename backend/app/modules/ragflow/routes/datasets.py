from fastapi import APIRouter

from backend.app.core.authz import AuthContextDep
from backend.app.core.datasets import list_visible_datasets
from backend.app.core.permdbg import permdbg

router = APIRouter()


@router.get("/datasets")
def list_datasets(
    ctx: AuthContextDep,
):
    """
    列出RAGFlow数据集（基于权限组过滤）

    权限规则：
    - 管理员：可以看到所有数据集
    - 其他角色：根据权限组的accessible_kbs配置
    """
    datasets = list_visible_datasets(ctx.deps, ctx.snapshot, ctx.user)
    try:
        permdbg(
            "ragflow.datasets.list",
            user=ctx.user.username,
            role=ctx.user.role,
            kb_scope=ctx.snapshot.kb_scope,
            kb_refs=sorted(list(ctx.snapshot.kb_names))[:50],
            datasets=[d.get("name") for d in datasets[:50] if isinstance(d, dict)],
        )
    except Exception:
        pass
    return {"datasets": datasets, "count": len(datasets)}
