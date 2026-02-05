from __future__ import annotations

import html
import io
import zipfile
from xml.etree import ElementTree as ET


_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def convert_docx_bytes_to_html_bytes_fallback(content: bytes) -> bytes:
    """
    Best-effort DOCX -> HTML conversion without external dependencies.

    This is intentionally simple: it extracts paragraph text from
    `word/document.xml` and emits a readable HTML document.
    """

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        try:
            xml_bytes = zf.read("word/document.xml")
        except KeyError as e:
            raise RuntimeError("invalid docx: missing word/document.xml") from e

    try:
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        raise RuntimeError("invalid docx: unable to parse document.xml") from e

    paras: list[str] = []
    for p in root.iter(f"{{{_W_NS}}}p"):
        parts: list[str] = []
        for node in p.iter():
            tag = node.tag
            if tag == f"{{{_W_NS}}}t":
                if node.text:
                    parts.append(html.escape(node.text))
            elif tag == f"{{{_W_NS}}}tab":
                parts.append("&emsp;")
            elif tag == f"{{{_W_NS}}}br":
                parts.append("<br/>")
        text = "".join(parts).strip()
        if text:
            paras.append(f"<p>{text}</p>")

    body = "\n".join(paras) if paras else "<p>(空文档)</p>"
    out = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>DOCX Preview</title>
    <style>
      body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, "Noto Sans", "PingFang SC", "Microsoft YaHei", sans-serif; line-height: 1.6; padding: 16px; }}
      p {{ margin: 0 0 10px; }}
    </style>
  </head>
  <body>
    {body}
  </body>
</html>
"""
    return out.encode("utf-8")

