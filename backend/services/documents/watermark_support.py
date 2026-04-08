from __future__ import annotations

import io
import json
import mimetypes
import urllib.parse
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi.responses import Response

from backend.services.watermarking import DocumentWatermarkService

VISIBLE_TEXT_WATERMARK_EXTENSIONS = {".txt", ".md", ".csv", ".log"}


@dataclass(frozen=True)
class DownloadArtifact:
    content: bytes
    filename: str
    media_type: str
    distribution_mode: str
    watermark: dict


class DocumentWatermarkSupport:
    def __init__(self, deps):
        self._deps = deps

    def content_disposition(self, filename: str) -> str:
        try:
            filename.encode("ascii")
            return f'attachment; filename="{filename}"'
        except UnicodeEncodeError:
            ascii_filename = filename.encode("ascii", "replace").decode("ascii")
            encoded_filename = urllib.parse.quote(filename)
            return f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"

    def watermark_service(self) -> DocumentWatermarkService:
        return DocumentWatermarkService(
            store=getattr(self._deps, "watermark_policy_store", None),
            org_structure_manager=getattr(self._deps, "org_structure_manager", None),
        )

    def build_watermark(
        self,
        *,
        ctx,
        purpose: str,
        doc_id: str,
        filename: str,
        source: str,
    ) -> dict:
        return self.watermark_service().build_watermark(
            user=getattr(ctx, "user", None),
            payload_sub=getattr(getattr(ctx, "payload", None), "sub", None),
            purpose=purpose,
            doc_id=doc_id,
            filename=filename,
            source=source,
        )

    @staticmethod
    def _decode_text_content(content: bytes) -> tuple[str, str]:
        for encoding in ("utf-8", "gbk"):
            try:
                return encoding, content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise RuntimeError("watermark_text_decode_failed")

    @staticmethod
    def _text_watermark_block(watermark_text: str) -> str:
        return "\n".join(
            [
                "[\u53d7\u63a7\u5206\u53d1\u6c34\u5370]",
                watermark_text,
                "[/\u53d7\u63a7\u5206\u53d1\u6c34\u5370]",
                "",
            ]
        )

    def _apply_text_watermark(self, *, content: bytes, watermark_text: str) -> bytes:
        encoding, decoded = self._decode_text_content(content)
        combined = f"{self._text_watermark_block(watermark_text)}\n{decoded}"
        return combined.encode(encoding)

    @staticmethod
    def package_filename(filename: str) -> str:
        path = Path(filename or "document")
        stem = path.stem or "document"
        return f"{stem}__controlled_distribution.zip"

    def build_controlled_package(
        self,
        *,
        filename: str,
        content: bytes,
        source: str,
        watermark: dict,
    ) -> bytes:
        service = self.watermark_service()
        note_text = service.build_distribution_note(
            watermark=watermark,
            filename=filename,
            source=source,
            item_count=1,
        )
        manifest = service.build_manifest(
            watermark=watermark,
            source=source,
            filename=filename,
            distribution_mode="controlled_package",
            documents=[{"doc_id": watermark.get("doc_id"), "filename": filename}],
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("00_CONTROLLED_DISTRIBUTION.txt", note_text.encode("utf-8"))
            zip_file.writestr(
                "watermark_manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            zip_file.writestr(filename, content)
        return buffer.getvalue()

    def rewrite_zip_with_watermark(
        self,
        *,
        zip_content: bytes,
        filename: str,
        source: str,
        watermark: dict,
        documents: list[dict],
    ) -> bytes:
        service = self.watermark_service()
        note_text = service.build_distribution_note(
            watermark=watermark,
            filename=filename,
            source=source,
            item_count=len(documents),
        )
        manifest = service.build_manifest(
            watermark=watermark,
            source=source,
            filename=filename,
            distribution_mode="batch_zip",
            documents=documents,
        )
        src = io.BytesIO(zip_content)
        dst = io.BytesIO()
        try:
            with zipfile.ZipFile(src, "r") as input_zip, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as output_zip:
                output_zip.writestr("00_CONTROLLED_DISTRIBUTION.txt", note_text.encode("utf-8"))
                output_zip.writestr(
                    "watermark_manifest.json",
                    json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
                )
                for info in input_zip.infolist():
                    output_zip.writestr(info.filename, input_zip.read(info.filename))
        except zipfile.BadZipFile as exc:
            raise RuntimeError("watermark_batch_zip_invalid") from exc
        return dst.getvalue()

    def build_download_artifact(
        self,
        *,
        content: bytes,
        filename: str,
        source: str,
        doc_id: str,
        ctx,
        media_type: str | None = None,
    ) -> DownloadArtifact:
        watermark = self.build_watermark(
            ctx=ctx,
            purpose="download",
            doc_id=doc_id,
            filename=filename,
            source=source,
        )
        ext = Path(filename or "").suffix.lower()
        if ext in VISIBLE_TEXT_WATERMARK_EXTENSIONS:
            return DownloadArtifact(
                content=self._apply_text_watermark(content=content, watermark_text=str(watermark.get("text") or "")),
                filename=filename,
                media_type=(media_type or mimetypes.guess_type(filename)[0] or "text/plain; charset=utf-8"),
                distribution_mode="inline_text_watermark",
                watermark=watermark,
            )

        return DownloadArtifact(
            content=self.build_controlled_package(
                filename=filename,
                content=content,
                source=source,
                watermark=watermark,
            ),
            filename=self.package_filename(filename),
            media_type="application/zip",
            distribution_mode="controlled_package",
            watermark=watermark,
        )

    def build_response(
        self,
        *,
        content: bytes,
        filename: str,
        media_type: str,
        distribution_mode: str,
        watermark: dict,
    ) -> Response:
        return self.download_response_from_artifact(
            DownloadArtifact(
                content=content,
                filename=filename,
                media_type=media_type,
                distribution_mode=distribution_mode,
                watermark=watermark,
            )
        )

    def download_response_from_artifact(self, artifact: DownloadArtifact) -> Response:
        return Response(
            content=artifact.content,
            media_type=artifact.media_type,
            headers={
                "Content-Disposition": self.content_disposition(artifact.filename),
                "X-Watermark-Policy-Id": str(artifact.watermark.get("policy_id") or ""),
                "X-Distribution-Mode": artifact.distribution_mode,
            },
        )
