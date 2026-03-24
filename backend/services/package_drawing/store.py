from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from backend.database.sqlite import connect_sqlite


@dataclass(frozen=True)
class PackageDrawingImage:
    image_id: str
    source_type: str
    image_url: str
    rel_path: str
    mime_type: str
    filename: str
    sort_order: int


@dataclass(frozen=True)
class PackageDrawingRecord:
    model: str
    barcode: str
    parameters: dict[str, str]
    images: list[PackageDrawingImage]


class PackageDrawingStore:
    def __init__(self, db_path: str):
        self._db_path = str(db_path)

    def upsert_record(
        self,
        *,
        model: str,
        barcode: str,
        parameters: dict[str, str],
        images: list[dict[str, Any]],
    ) -> list[str]:
        now_ms = int(time.time() * 1000)
        old_paths: list[str] = []
        with connect_sqlite(self._db_path) as conn:
            row = conn.execute(
                "SELECT created_at_ms FROM package_drawing_records WHERE model = ?",
                (model,),
            ).fetchone()
            created_at_ms = int(row["created_at_ms"]) if row and row["created_at_ms"] is not None else now_ms

            cur = conn.execute(
                """
                SELECT rel_path
                FROM package_drawing_images
                WHERE model = ? AND source_type = 'embedded' AND rel_path IS NOT NULL AND rel_path <> ''
                """,
                (model,),
            )
            for item in cur.fetchall():
                rel_path = str(item["rel_path"] or "").strip()
                if rel_path:
                    old_paths.append(rel_path)

            conn.execute(
                """
                INSERT INTO package_drawing_records(model, barcode, parameters_json, created_at_ms, updated_at_ms)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(model) DO UPDATE SET
                    barcode = excluded.barcode,
                    parameters_json = excluded.parameters_json,
                    updated_at_ms = excluded.updated_at_ms
                """,
                (model, barcode or "", json.dumps(parameters or {}, ensure_ascii=False), created_at_ms, now_ms),
            )

            conn.execute("DELETE FROM package_drawing_images WHERE model = ?", (model,))

            for index, image in enumerate(images or []):
                conn.execute(
                    """
                    INSERT INTO package_drawing_images(
                        image_id, model, source_type, image_url, rel_path, mime_type, filename, sort_order, created_at_ms
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(image.get("image_id") or "").strip(),
                        model,
                        str(image.get("source_type") or "").strip(),
                        str(image.get("image_url") or ""),
                        str(image.get("rel_path") or ""),
                        str(image.get("mime_type") or ""),
                        str(image.get("filename") or ""),
                        int(image.get("sort_order") if image.get("sort_order") is not None else index),
                        now_ms,
                    ),
                )
            conn.commit()
        return old_paths

    def get_record(self, model: str) -> PackageDrawingRecord | None:
        with connect_sqlite(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT model, barcode, parameters_json
                FROM package_drawing_records
                WHERE model = ?
                """,
                (model,),
            ).fetchone()
            if row is None:
                return None

            try:
                parameters = json.loads(row["parameters_json"] or "{}")
            except Exception:
                parameters = {}
            if not isinstance(parameters, dict):
                parameters = {}
            normalized_params: dict[str, str] = {}
            for key, value in parameters.items():
                if not isinstance(key, str):
                    continue
                k = key.strip()
                if not k:
                    continue
                normalized_params[k] = str(value) if value is not None else ""

            image_rows = conn.execute(
                """
                SELECT image_id, source_type, image_url, rel_path, mime_type, filename, sort_order
                FROM package_drawing_images
                WHERE model = ?
                ORDER BY sort_order ASC, created_at_ms ASC
                """,
                (model,),
            ).fetchall()
            images = [
                PackageDrawingImage(
                    image_id=str(item["image_id"] or ""),
                    source_type=str(item["source_type"] or ""),
                    image_url=str(item["image_url"] or ""),
                    rel_path=str(item["rel_path"] or ""),
                    mime_type=str(item["mime_type"] or ""),
                    filename=str(item["filename"] or ""),
                    sort_order=int(item["sort_order"] or 0),
                )
                for item in image_rows
            ]

            return PackageDrawingRecord(
                model=str(row["model"] or ""),
                barcode=str(row["barcode"] or ""),
                parameters=normalized_params,
                images=images,
            )

    def get_image(self, image_id: str) -> PackageDrawingImage | None:
        with connect_sqlite(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT image_id, source_type, image_url, rel_path, mime_type, filename, sort_order
                FROM package_drawing_images
                WHERE image_id = ?
                """,
                (image_id,),
            ).fetchone()
            if row is None:
                return None
            return PackageDrawingImage(
                image_id=str(row["image_id"] or ""),
                source_type=str(row["source_type"] or ""),
                image_url=str(row["image_url"] or ""),
                rel_path=str(row["rel_path"] or ""),
                mime_type=str(row["mime_type"] or ""),
                filename=str(row["filename"] or ""),
                sort_order=int(row["sort_order"] or 0),
            )
