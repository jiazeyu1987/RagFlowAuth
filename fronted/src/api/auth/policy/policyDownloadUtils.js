export function extractFilenameFromContentDisposition(contentDisposition, fallbackName) {
  let filename = fallbackName;
  if (!contentDisposition) {
    return filename;
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;\s]+)/i);
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch (_err) {
      return utf8Match[1];
    }
  }

  const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
  if (filenameMatch && filenameMatch[1]) {
    filename = filenameMatch[1].replace(/['"]/g, '');
  }
  return filename;
}

export function triggerBlobDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
