"""文档解析工具（M1-4 将完整实现文本提取）。

当前提供：
- 文件扩展名识别 → 格式分类（用于 E1 校验）；
- PDF 页数读取（用于页数校验）。

说明：PyMuPDF 读取 PDF 页数时若文本层为空即视为扫描版（E2，M1-4 处理）。
"""

from pathlib import Path


def get_file_extension(filename: str) -> str:
    """返回小写扩展名（含点），如 'foo.PDF' → '.pdf'。"""
    return Path(filename).suffix.lower()


def is_pdf(filename: str) -> bool:
    return get_file_extension(filename) == ".pdf"


def count_pdf_pages(file_bytes: bytes) -> int:
    """读取 PDF 页数（用于 ≤200 页校验）。非 PDF 文件调用方不得调用。"""
    import pymupdf  # PyMuPDF（延迟导入，避免未使用路径拉高启动开销）

    with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
        return doc.page_count


def html_to_text(html: str) -> str:
    """将 HTML 转为纯文本（URL 解析用，PRD F3：抓取 html 转文本）。

    保留脚本/样式外的正文文字，多空白归一化为单空格。
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    # 移除脚本与样式，避免混入非正文内容
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    text = soup.get_text(separator=" ")
    return " ".join(text.split())
