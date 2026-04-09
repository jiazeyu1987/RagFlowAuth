from __future__ import annotations

import asyncio
import json
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import assert_tool_allowed

router = APIRouter()

DATA_FILE = Path(__file__).with_name("province_urls.json")
TIMEOUT_SECONDS = 10
MAX_VERIFY_WORKERS = 8
VALID_HTTP_CODES = set(range(200, 400)) | {403, 412}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class ProvinceItem(BaseModel):
    name: str
    urls: list[str] = Field(default_factory=list)


class ProvinceListResponse(BaseModel):
    validated_on: str = ""
    source: str = ""
    provinces: list[ProvinceItem] = Field(default_factory=list)
    count: int = 0


class ResolveProvinceRequest(BaseModel):
    province: str = Field(default="", min_length=1, max_length=128)


class ResolveProvinceResponse(BaseModel):
    province: str
    ok: bool
    code: int | None = None
    url: str = ""
    errors: list[str] = Field(default_factory=list)


class VerifyProvinceRow(BaseModel):
    province: str
    ok: bool
    code: int | None = None
    url: str = ""
    errors: list[str] = Field(default_factory=list)


class VerifyAllResponse(BaseModel):
    total: int = 0
    success: int = 0
    failed: int = 0
    rows: list[VerifyProvinceRow] = Field(default_factory=list)


@lru_cache(maxsize=1)
def _load_payload() -> dict:
    if not DATA_FILE.exists():
        raise RuntimeError(f"drug_admin_data_missing:{DATA_FILE}")
    with DATA_FILE.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise RuntimeError("drug_admin_data_invalid")
    return payload


def _normalize_provinces(payload: dict) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for item in payload.get("provinces", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        urls_raw = item.get("urls") or []
        urls = [str(url).strip() for url in urls_raw if str(url).strip()]
        if name and urls:
            out.append({"name": name, "urls": urls})
    return out


def _province_map() -> tuple[dict, dict[str, list[str]]]:
    payload = _load_payload()
    provinces = _normalize_provinces(payload)
    return payload, {str(item["name"]): list(item["urls"]) for item in provinces}


def _check_url(url: str) -> tuple[bool, int | None, str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ssl_context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=ssl_context) as response:
            code = response.getcode() or 200
            final_url = response.geturl() or url
            return code in VALID_HTTP_CODES, int(code), str(final_url), ""
    except urllib.error.HTTPError as exc:
        code = int(exc.code)
        final_url = str(exc.geturl() or url)
        if code in VALID_HTTP_CODES:
            return True, code, final_url, ""
        return False, code, final_url, str(exc)
    except Exception as exc:
        return False, None, url, str(exc)


def _find_reachable_url(urls: list[str]) -> tuple[bool, int | None, str, list[str]]:
    errors: list[str] = []
    for raw in urls:
        url = str(raw or "").strip()
        if not url:
            continue
        ok, code, final_url, error = _check_url(url)
        if ok:
            return True, code, final_url, errors
        reason = error or "request_failed"
        errors.append(f"{url} -> {code if code is not None else 'connect_failed'} ({reason})")
    return False, None, "", errors


def _verify_all(provinces: list[dict[str, object]]) -> list[dict[str, object]]:
    if not provinces:
        return []
    rows: list[dict[str, object] | None] = [None] * len(provinces)

    def _check_one(index: int, row: dict[str, object]) -> tuple[int, dict[str, object]]:
        name = str(row.get("name") or "").strip()
        urls = [str(u).strip() for u in (row.get("urls") or []) if str(u).strip()]
        ok, code, final_url, errors = _find_reachable_url(urls)
        return index, {
            "province": name,
            "ok": bool(ok),
            "code": code,
            "url": final_url or "",
            "errors": errors,
        }

    max_workers = max(1, min(MAX_VERIFY_WORKERS, len(provinces)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_check_one, idx, row) for idx, row in enumerate(provinces)]
        for future in as_completed(futures):
            idx, result = future.result()
            rows[idx] = result
    return [row for row in rows if row is not None]


@router.get("/drug-admin/provinces", response_model=ProvinceListResponse)
async def list_drug_admin_provinces(ctx: AuthContextDep):  # noqa: ARG001
    assert_tool_allowed(ctx.snapshot, "drug_admin")
    payload, _ = _province_map()
    provinces = _normalize_provinces(payload)
    return {
        "validated_on": str(payload.get("validated_on") or ""),
        "source": str(payload.get("source") or ""),
        "provinces": provinces,
        "count": len(provinces),
    }


@router.post("/drug-admin/resolve", response_model=ResolveProvinceResponse)
async def resolve_drug_admin_province(body: ResolveProvinceRequest, ctx: AuthContextDep):  # noqa: ARG001
    assert_tool_allowed(ctx.snapshot, "drug_admin")
    _, mapping = _province_map()
    province = str(body.province or "").strip()
    urls = mapping.get(province)
    if not urls:
        raise HTTPException(status_code=404, detail="province_not_found")

    ok, code, final_url, errors = await asyncio.to_thread(_find_reachable_url, list(urls))
    return {
        "province": province,
        "ok": bool(ok),
        "code": code,
        "url": final_url or "",
        "errors": errors,
    }


@router.post("/drug-admin/verify", response_model=VerifyAllResponse)
async def verify_drug_admin_provinces(ctx: AuthContextDep):  # noqa: ARG001
    assert_tool_allowed(ctx.snapshot, "drug_admin")
    payload, _ = _province_map()
    provinces = _normalize_provinces(payload)
    rows = await asyncio.to_thread(_verify_all, provinces)
    success = sum(1 for row in rows if bool(row.get("ok")))
    total = len(rows)
    return {
        "total": total,
        "success": success,
        "failed": total - success,
        "rows": rows,
    }
