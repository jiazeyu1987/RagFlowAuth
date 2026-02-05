from __future__ import annotations

import base64
from pathlib import Path


def build_preview_payload(file_content: bytes, filename: str | None, doc_id: str | None = None) -> dict:
    """
    Return a unified preview JSON payload compatible with the Ragflow preview contract:
      - text: {type:'text', filename, content}
      - image: {type:'image', filename, content(base64), image_type}
      - pdf: {type:'pdf', filename, content(base64)}
      - html (office conversion): {type:'html', filename, content(base64)}
      - unsupported: {type:'unsupported', filename, message}
    """
    filename = filename or (f"document_{doc_id}" if doc_id else "document")
    file_ext = Path(filename).suffix.lower()

    text_extensions = {".txt", ".md", ".csv", ".json", ".xml", ".log", ".svg", ".html", ".css", ".js"}
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

    if file_ext in text_extensions:
        try:
            text_content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text_content = file_content.decode("gbk")
            except Exception:
                return {"type": "unsupported", "filename": filename, "message": "无法解码文本文件"}
        return {"type": "text", "filename": filename, "content": text_content}

    if file_ext in image_extensions:
        base64_image = base64.b64encode(file_content).decode("utf-8")
        image_type = file_ext[1:]
        return {"type": "image", "filename": filename, "content": base64_image, "image_type": image_type}

    if file_ext == ".pdf":
        base64_pdf = base64.b64encode(file_content).decode("utf-8")
        return {"type": "pdf", "filename": filename, "content": base64_pdf}

    if file_ext in {".doc", ".docx"}:
        try:
            from backend.services.office_to_html import convert_office_bytes_to_html_bytes

            html_bytes = convert_office_bytes_to_html_bytes(
                file_content, filename=filename or ("input.docx" if file_ext == ".docx" else "input.doc")
            )
            base64_html = base64.b64encode(html_bytes).decode("utf-8")
            out_name = f"{Path(filename).stem}.html" if filename else f"document_{doc_id}.html"
            return {"type": "html", "filename": out_name, "source_filename": filename, "content": base64_html}
        except Exception as e:
            label = "DOCX" if file_ext == ".docx" else "DOC"
            if file_ext == ".docx" and "soffice not found" in str(e).lower():
                try:
                    from backend.services.docx_to_html_fallback import convert_docx_bytes_to_html_bytes_fallback

                    html_bytes = convert_docx_bytes_to_html_bytes_fallback(file_content)
                    base64_html = base64.b64encode(html_bytes).decode("utf-8")
                    out_name = f"{Path(filename).stem}.html" if filename else f"document_{doc_id}.html"
                    return {"type": "html", "filename": out_name, "source_filename": filename, "content": base64_html}
                except Exception as e2:
                    return {"type": "unsupported", "filename": filename, "message": f"DOCX preview unavailable: {str(e2)}"}
            return {"type": "unsupported", "filename": filename, "message": f"{label} preview unavailable: {str(e)}"}

    if file_ext in {".xlsx", ".xls"}:
        try:
            from backend.services.office_to_html import convert_office_bytes_to_html_bytes

            html_bytes = convert_office_bytes_to_html_bytes(file_content, filename=filename or "input.xlsx")
            base64_html = base64.b64encode(html_bytes).decode("utf-8")
            out_name = f"{Path(filename).stem}.html" if filename else f"document_{doc_id}.html"
            return {"type": "html", "filename": out_name, "source_filename": filename, "content": base64_html}
        except Exception as e:
            return {"type": "unsupported", "filename": filename, "message": f"Excel 在线预览不可用：{str(e)}"}

    return {"type": "unsupported", "filename": filename, "message": f"不支持的文件类型: {file_ext}，请下载后查看"}
