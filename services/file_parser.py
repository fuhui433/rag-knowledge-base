"""
多格式文件解析服务
支持: TXT, MD, PDF, DOCX, CSV, XLSX
"""

import io
import csv as csv_module


class FileParser:
    """文件解析器，根据文件扩展名选择对应的解析方法"""

    @staticmethod
    def parse(file_bytes: bytes, filename: str) -> str:
        """根据文件名后缀解析文件内容，返回纯文本字符串"""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        parsers = {
            "txt": FileParser._parse_txt,
            "md": FileParser._parse_txt,
            "csv": FileParser._parse_csv,
            "pdf": FileParser._parse_pdf,
            "docx": FileParser._parse_docx,
            "xlsx": FileParser._parse_xlsx,
        }

        parser = parsers.get(ext)
        if parser is None:
            raise ValueError(f"不支持的文件格式: .{ext}")

        return parser(file_bytes)

    # ----- TXT / MD -----
    @staticmethod
    def _parse_txt(file_bytes: bytes) -> str:
        for encoding in ("utf-8", "gbk", "latin-1"):
            try:
                return file_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("无法解码文件，请确认文件编码为 UTF-8 或 GBK")

    # ----- CSV -----
    @staticmethod
    def _parse_csv(file_bytes: bytes) -> str:
        # 尝试多种编码
        for encoding in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
            try:
                text = file_bytes.decode(encoding)
                reader = csv_module.reader(io.StringIO(text))
                rows = [" | ".join(row) for row in reader]
                return "\n".join(rows)
            except (UnicodeDecodeError, csv_module.Error):
                continue
        raise ValueError("无法解析 CSV 文件")

    # ----- PDF -----
    @staticmethod
    def _parse_pdf(file_bytes: bytes) -> str:
        # 优先用 pdfplumber（提取效果更好），回退到 PyPDF2
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            result = "\n".join(text_parts).strip()
            if result:
                return result
        except Exception:
            pass

        # 回退 PyPDF2
        from PyPDF2 import PdfReader
        text_parts = []
        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        result = "\n".join(text_parts).strip()
        if not result:
            raise ValueError("PDF 中未提取到文本内容（可能为扫描件或图片型 PDF）")
        return result

    # ----- DOCX -----
    @staticmethod
    def _parse_docx(file_bytes: bytes) -> str:
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    # ----- XLSX -----
    @staticmethod
    def _parse_xlsx(file_bytes: bytes) -> str:
        import pandas as pd

        # 读取所有 sheet
        sheets = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
        text_parts = []
        for sheet_name, df in sheets.items():
            # 跳过空 sheet
            df = df.dropna(how="all")
            if df.empty:
                continue
            text_parts.append(f"--- Sheet: {sheet_name} ---")
            # 转为可读文本
            text_parts.append(df.to_csv(index=False, encoding="utf-8"))
        return "\n".join(text_parts)
