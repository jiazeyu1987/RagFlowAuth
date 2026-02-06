from __future__ import annotations

import base64
import html
import io
from pathlib import Path


def _xlsx_bytes_to_sheets_html(file_content: bytes, *, max_rows: int = 200, max_cols: int = 60) -> dict[str, str]:
    """
    Convert an .xlsx file to a lightweight HTML table per sheet (no styles/shapes).

    This is intentionally "lossy": shapes/flowcharts and rich formatting are not preserved.
    For those cases callers can request `render=html` to get an "original preview" HTML.
    """
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True, data_only=True)
    sheets: dict[str, str] = {}

    for ws in wb.worksheets:
        rows_html: list[str] = []
        for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if r_idx > max_rows:
                break
            cells = []
            for c_idx, value in enumerate(row, start=1):
                if c_idx > max_cols:
                    break
                text = "" if value is None else str(value)
                cells.append(f"<td>{html.escape(text)}</td>")
            rows_html.append("<tr>" + "".join(cells) + "</tr>")
        table_html = "<table><tbody>" + "".join(rows_html) + "</tbody></table>"
        title = str(ws.title or f"Sheet{len(sheets) + 1}")
        sheets[title] = table_html

    return sheets


def _sheets_html_to_single_html(sheets: dict[str, str]) -> bytes:
    parts: list[str] = [
        "<!doctype html><html><head><meta charset=\"utf-8\" />",
        "<title>Excel Preview</title>",
        "<style>",
        "body{font-family:system-ui,Segoe UI,Arial; padding:16px;} h3{margin:18px 0 10px 0;}",
        "table{border-collapse:collapse; width:100%;} td,th{border:1px solid #ddd;padding:6px 8px;vertical-align:top;}",
        "tr:nth-child(even){background:#fafafa}",
        "</style>",
        "</head><body>",
    ]
    for name, table in sheets.items():
        parts.append(f"<h3>{html.escape(name)}</h3>")
        parts.append(table)
    parts.append("</body></html>")
    return "\n".join(parts).encode("utf-8")


def build_preview_payload(file_content: bytes, filename: str | None, doc_id: str | None = None, *, render: str = "default") -> dict:
    """
    Return a unified preview JSON payload:
      - text:  {type:'text', filename, content}
      - image: {type:'image', filename, content(base64), image_type}
      - pdf:   {type:'pdf', filename, content(base64)}
      - html:  {type:'html', filename, source_filename, content(base64)}
      - excel: {type:'excel', filename, sheets:{sheetName: html}}
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
        mode = (render or "default").strip().lower()

        if mode != "html":
            if file_ext == ".xlsx":
                try:
                    sheets = _xlsx_bytes_to_sheets_html(file_content)
                    return {"type": "excel", "filename": filename, "sheets": sheets}
                except Exception as e:
                    return {"type": "unsupported", "filename": filename, "message": f"Excel 预览失败：{str(e)}"}
            return {"type": "unsupported", "filename": filename, "message": "暂不支持 .xls 在线预览（请下载查看）"}

        # render=html
        try:
            from backend.services.office_to_html import convert_office_bytes_to_html_bytes

            html_bytes = convert_office_bytes_to_html_bytes(file_content, filename=filename or "input.xlsx")
            base64_html = base64.b64encode(html_bytes).decode("utf-8")
            out_name = f"{Path(filename).stem}.html" if filename else f"document_{doc_id}.html"
            return {"type": "html", "filename": out_name, "source_filename": filename, "content": base64_html}
        except Exception:
            if file_ext == ".xlsx":
                try:
                    sheets = _xlsx_bytes_to_sheets_html(file_content)
                    html_bytes = _sheets_html_to_single_html(sheets)
                    base64_html = base64.b64encode(html_bytes).decode("utf-8")
                    out_name = f"{Path(filename).stem}.html" if filename else f"document_{doc_id}.html"
                    return {"type": "html", "filename": out_name, "source_filename": filename, "content": base64_html}
                except Exception as e2:
                    return {"type": "unsupported", "filename": filename, "message": f"Excel 原样预览(HTML)失败：{str(e2)}"}
            return {"type": "unsupported", "filename": filename, "message": "暂不支持 .xls 原样预览(HTML)（请下载查看）"}

    return {"type": "unsupported", "filename": filename, "message": f"不支持的文件类型: {file_ext}（请下载后查看）"}

