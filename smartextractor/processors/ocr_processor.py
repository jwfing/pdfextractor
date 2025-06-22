"""
OCR Processor - Responsible for optical character recognition
"""

from typing import List, Optional
from loguru import logger

from ..config import ExtractionConfig
from ..models import TextBlock
from ..exceptions import OCRError, OCRNotAvailableError


class OCRProcessor:
    """OCR Processor"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        self._init_ocr_engines()
    
    def _init_ocr_engines(self):
        """Initialize OCR engines"""
        self.tesseract_available = self._check_tesseract()
        self.easyocr_available = self._check_easyocr()
        
        if not self.tesseract_available and not self.easyocr_available:
            logger.warning("No OCR engines available")
    
    def _check_tesseract(self) -> bool:
        """Check if Tesseract is available"""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
    
    def _check_easyocr(self) -> bool:
        """Check if EasyOCR is available"""
        try:
            import easyocr
            return True
        except ImportError:
            return False
    
    def process_page(self, page_data, page_num: int) -> List[TextBlock]:
        """Process page OCR"""
        try:
            # Here should implement specific OCR logic
            # Temporarily return empty list
            logger.info(f"OCR processing page {page_num}")
            return []
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            raise OCRError(f"OCR processing failed: {e}")
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        languages = []
        
        if self.tesseract_available:
            try:
                import pytesseract
                languages.extend(pytesseract.get_languages())
            except Exception:
                pass
        
        if self.easyocr_available:
            # Languages supported by EasyOCR
            languages.extend(['ch_sim', 'en', 'ja', 'ko'])
        
        return list(set(languages)) 