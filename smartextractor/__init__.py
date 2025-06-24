"""
SmartExtractor - 智能PDF文本提取库

集成图像识别与版式自动检测功能，能够智能、准确地提取PDF文档中的文本内容。
"""

from .core import SmartExtractor
from .adaptive_pdfitz import AdaptiveFitzExtractor
from .config import ExtractionConfig
from .models import ExtractionResult, PageResult, TableResult, ImageResult
from .exceptions import SmartExtractorError, PDFProcessingError, OCRError

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

__all__ = [
    "SmartExtractor",
    "AdaptiveFitzExtractor",
    "ExtractionConfig", 
    "ExtractionResult",
    "PageResult",
    "TableResult",
    "ImageResult",
    "SmartExtractorError",
    "PDFProcessingError",
    "OCRError",
] 