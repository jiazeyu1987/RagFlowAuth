from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import logging
from pydantic import BaseModel

from app.core.auth import AuthRequired, get_deps
from app.core.permission_resolver import ResourceScope, resolve_permissions
from dependencies import AppDependencies


router = APIRouter()
logger = logging.getLogger(__name__)


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
    payload: AuthRequired,
    deps: AppDependencies = Depends(get_deps),
):
    """
    在知识库中检索文本块（chunks）（基于权限组）

    权限规则：
    - 管理员：可以检索所有知识库
    - 其他角色：只能检索权限组中配置的知识库
    """
    user = deps.user_store.get_by_user_id(payload.sub)

    logger.info(f"[SEARCH] User: {user.username}, question: {request_data.question[:50] if len(request_data.question) > 50 else request_data.question}...")

    # 获取用户有权限的知识库（基于权限组）
    if user.role == "admin":
        # 管理员可以使用所有知识库
        all_datasets = deps.ragflow_service.list_datasets()
        available_dataset_ids = [ds["id"] for ds in all_datasets]
        logger.info(f"[SEARCH] Admin user, available datasets: {available_dataset_ids}")
    else:
        snapshot = resolve_permissions(deps, user)
        if snapshot.kb_scope == ResourceScope.NONE:
            available_dataset_ids = []
        else:
            all_datasets = deps.ragflow_service.list_datasets()
            name_to_id = {ds["name"]: ds["id"] for ds in all_datasets if ds.get("name") and ds.get("id")}
            available_dataset_ids = [name_to_id[kb_name] for kb_name in snapshot.kb_names if kb_name in name_to_id]

    # 如果指定了dataset_ids，验证用户是否有权限
    if request_data.dataset_ids:
        valid_dataset_ids = [ds_id for ds_id in request_data.dataset_ids if ds_id in available_dataset_ids]
        if not valid_dataset_ids:
            raise HTTPException(status_code=403, detail="您没有权限访问指定的知识库")
        dataset_ids = valid_dataset_ids
    else:
        dataset_ids = available_dataset_ids

    if not dataset_ids:
        raise HTTPException(status_code=403, detail="no_accessible_knowledge_bases")

    logger.info(f"[SEARCH] Using datasets: {dataset_ids}")

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

        logger.info(f"[SEARCH] Found {result.get('total', 0)} chunks")

        return result
    except Exception as e:
        logger.error(f"[SEARCH] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@router.get("/datasets")
async def list_available_datasets(
    payload: AuthRequired,
    deps: AppDependencies = Depends(get_deps),
):
    """
    获取用户可用的知识库列表（基于权限组）

    权限规则：
    - 管理员：可以看到所有知识库
    - 其他角色：根据权限组的accessible_kbs配置
    """
    logger.info("=" * 80)
    logger.info("[GET /api/datasets from agents.py] Called")

    user = deps.user_store.get_by_user_id(payload.sub)
    logger.info(f"[GET /api/datasets] Current user: {user.username}, role: {user.role}, group_id: {user.group_id}")

    # 获取所有知识库从RAGFlow
    all_datasets = deps.ragflow_service.list_datasets()
    logger.info(f"[GET /api/datasets] Total datasets from RAGFlow: {len(all_datasets)}")
    for ds in all_datasets:
        logger.info(f"  - Dataset: id={ds.get('id')}, name={ds.get('name')}")

    # 管理员返回所有知识库
    if user.role == "admin":
        logger.info(f"[GET /api/datasets] Admin user showing all datasets")
        return {
            "datasets": all_datasets,
            "count": len(all_datasets)
        }

    snapshot = resolve_permissions(deps, user)
    if snapshot.kb_scope == ResourceScope.NONE:
        return {"datasets": [], "count": 0}

    filtered = [ds for ds in all_datasets if ds.get("name") in snapshot.kb_names]
    return {"datasets": filtered, "count": len(filtered)}
