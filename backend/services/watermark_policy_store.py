from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.database.sqlite import connect_sqlite


@dataclass(frozen=True)
class WatermarkPolicy:
    policy_id: str
    name: str
    text_template: str
    label_text: str
    text_color: str
    opacity: float
    rotation_deg: int
    gap_x: int
    gap_y: int
    font_size: int
    is_active: bool


class WatermarkPolicyStore:
    def __init__(self, *, db_path: str | Path):
        self._db_path = str(db_path)

    def get_active_policy(self) -> WatermarkPolicy:
        with connect_sqlite(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT
                    policy_id,
                    name,
                    text_template,
                    label_text,
                    text_color,
                    opacity,
                    rotation_deg,
                    gap_x,
                    gap_y,
                    font_size,
                    is_active
                FROM watermark_policies
                WHERE is_active = 1
                ORDER BY updated_at_ms DESC, created_at_ms DESC
                LIMIT 1
                """
            ).fetchone()

        if not row:
            raise RuntimeError("active_watermark_policy_missing")

        return WatermarkPolicy(
            policy_id=str(row[0] or ""),
            name=str(row[1] or ""),
            text_template=str(row[2] or ""),
            label_text=str(row[3] or ""),
            text_color=str(row[4] or "#6b7280"),
            opacity=float(row[5] if row[5] is not None else 0.18),
            rotation_deg=int(row[6] if row[6] is not None else -24),
            gap_x=int(row[7] if row[7] is not None else 260),
            gap_y=int(row[8] if row[8] is not None else 180),
            font_size=int(row[9] if row[9] is not None else 18),
            is_active=bool(row[10]),
        )
