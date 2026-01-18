from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import ResourceScope, allowed_dataset_ids, filter_datasets_by_name


router = APIRouter()
logger = logging.getLogger(__name__)
perm_logger = logging.getLogger("uvicorn.error")


class SearchRequest(BaseModel):
    """Search request model"""
    question: str
    dataset_ids: Optional[list[str]] = None
    page: int = 1
    page_size: int = 30
    similarity_threshold: float = 0.2
    top_k: int = 30
    keyword: bool = False
    highlight: bool = False


@router.post("/search")
async def search_chunks(
    request_data: SearchRequest,
    ctx: AuthContextDep,
):
    """
    在知识库中检索文本块（chunks）（基于权限组）

    权限规则：
    - 管理员：可以检索所有知识库
    - 其他角色：只能检索权限组中配置的知识库
    """
    deps = ctx.deps
    snapshot = ctx.snapshot

    all_datasets = deps.ragflow_service.list_datasets()
    available_dataset_ids = allowed_dataset_ids(snapshot, all_datasets)

    try:
        perm_logger.info(
            "[PERMDBG] /api/search user=%s role=%s kb_scope=%s requested=%s allowed_ids=%s",
            ctx.user.username,
            ctx.user.role,
            snapshot.kb_scope,
            (request_data.dataset_ids or [])[:50],
            available_dataset_ids[:50],
        )
    except Exception:
        pass

    # 如果指定了dataset_ids，验证用户是否有权限
    if request_data.dataset_ids:
        normalize = getattr(deps.ragflow_service, "normalize_dataset_ids", None)
        requested_ids = normalize(request_data.dataset_ids) if callable(normalize) else request_data.dataset_ids
        valid_dataset_ids = [ds_id for ds_id in requested_ids if ds_id in available_dataset_ids]
        if not valid_dataset_ids:
            raise HTTPException(status_code=403, detail="您没有权限访问指定的知识库")
        dataset_ids = valid_dataset_ids
    else:
        dataset_ids = available_dataset_ids

    if not dataset_ids:
        raise HTTPException(status_code=403, detail="no_accessible_knowledge_bases")

    # 调用检索服务
    try:
        result = deps.ragflow_chat_service.retrieve_chunks(
            question=request_data.question,
            dataset_ids=dataset_ids,
            page=request_data.page,
            page_size=request_data.page_size,
            similarity_threshold=request_data.similarity_threshold,
            top_k=request_data.top_k,
            keyword=request_data.keyword,
            highlight=request_data.highlight
        )

        return result
    except Exception as e:
        logger.error(f"[SEARCH] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@router.get("/datasets")
async def list_available_datasets(
    ctx: AuthContextDep,
):
    """
    获取用户可用的知识库列表（基于权限组）

    权限规则：
    - 管理员：可以看到所有知识库
    - 其他角色：根据权限组的accessible_kbs配置
    """
    deps = ctx.deps
    snapshot = ctx.snapshot

    # 获取所有知识库从RAGFlow
    all_datasets = deps.ragflow_service.list_datasets()

    if snapshot.is_admin:
        return {"datasets": all_datasets, "count": len(all_datasets)}

    filtered = filter_datasets_by_name(snapshot, all_datasets)
    try:
        perm_logger.info(
            "[PERMDBG] /api/datasets user=%s role=%s kb_scope=%s kb_refs=%s -> datasets=%s",
            ctx.user.username,
            ctx.user.role,
            snapshot.kb_scope,
            sorted(list(snapshot.kb_names))[:50],
            [d.get("name") for d in filtered[:50] if isinstance(d, dict)],
        )
    except Exception:
        pass
    return {"datasets": filtered, "count": len(filtered)}
