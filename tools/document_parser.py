import os
import io
from pathlib import Path
from pypdf import PdfReader
import docx
from langchain_core.tools import tool

class DocumentParser:
    @staticmethod
    def parse_pdf(file_path: str | Path) -> str:
        try:
            reader = PdfReader(str(file_path))
            text_blocks = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_blocks.append(f"--- Page {i+1} ---\n{text}")
            return "\n".join(text_blocks)
        except Exception as e:
            return f"Error parsing PDF '{file_path}': {str(e)}"

    @staticmethod
    def parse_docx(file_path: str | Path) -> str:
        try:
            doc = docx.Document(str(file_path))
            text_blocks = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_blocks.append(para.text)
            return "\n".join(text_blocks)
        except Exception as e:
            return f"Error parsing DOCX '{file_path}': {str(e)}"

    @staticmethod
    def parse(file_path: str) -> str:
        """
        Auto-detects file extension and routes to correct parser.
        """
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found at {file_path}"
            
        ext = path.suffix.lower()
        if ext == '.pdf':
            return DocumentParser.parse_pdf(path)
        elif ext == '.docx':
            return DocumentParser.parse_docx(path)
        elif ext in ['.txt', '.md', '.csv']:
             try:
                 with open(path, 'r', encoding='utf-8') as f:
                     return f.read()
             except Exception as e:
                 return f"Error reading text file '{file_path}': {str(e)}"
        else:
            return f"Error: Unsupported file type '{ext}'"

_parser_instance = DocumentParser()

@tool
def parse_document(file_path: str) -> str:
    """
    Parses a local file (PDF, DOCX, TXT, MD) and returns the extracted raw text.
    Use this to read user uploaded resumes, course syllabi, or exported logs.
    
    Args:
        file_path: Absolute or relative local path to the document.
    """
    return _parser_instance.parse(file_path)
