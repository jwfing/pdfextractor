"""
Core Module - Main implementation of SmartExtractor
"""

import os
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger

from .config import ExtractionConfig
from .models import ExtractionResult, PageResult, TextBlock, TableResult, ImageResult
from .exceptions import (
    SmartExtractorError, PDFNotFoundError, PDFCorruptedError,
    ConfigurationError, ProcessingTimeoutError, PDFPasswordProtectedError,
    OCRError, LayoutDetectionError, TableExtractionError, ImageProcessingError,
    ValidationError, UnsupportedFormatError
)
from .processors.pdf_processor import PDFProcessor
from .processors.ocr_processor import OCRProcessor
from .processors.layout_processor import LayoutProcessor
from .processors.table_processor import TableProcessor
from .processors.image_processor import ImageProcessor
from .processors.text_processor import TextProcessor


class SmartExtractor:
    """Intelligent PDF Text Extractor"""
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        """
        Initialize SmartExtractor
        
        Args:
            config: Extraction config, use default if None
        """
        self.config = config or ExtractionConfig()
        
        # Initialize processors
        self._init_processors()
        
        logger.info("SmartExtractor initialized")
    
    def _init_processors(self):
        """Initialize all processors"""
        try:
            self.pdf_processor = PDFProcessor(self.config)
            self.ocr_processor = OCRProcessor(self.config) if self.config.enable_ocr else None
            self.layout_processor = LayoutProcessor(self.config) if self.config.enable_layout_detection else None
            self.table_processor = TableProcessor(self.config) if self.config.enable_table_extraction else None
            self.image_processor = ImageProcessor(self.config) if self.config.enable_image_processing else None
            self.text_processor = TextProcessor(self.config) if self.config.enable_text_cleaning else None
            
        except Exception as e:
            logger.error(f"Processor initialization failed: {e}")
            raise ConfigurationError(f"Processor initialization failed: {e}")
    
    def extract_text(self, pdf_path: str) -> str:
        """
        Extract PDF text (simple version)
        
        Args:
            pdf_path: PDF file path
            
        Returns:
            Extracted text content
        """
        result = self.extract(pdf_path)
        return result.text
    
    def extract(self, pdf_path: str) -> ExtractionResult:
        """
        Extract PDF content (full version)
        
        Args:
            pdf_path: PDF file path
            
        Returns:
            Full extraction result
        """
        start_time = time.time()
        
        try:
            # Validate file
            self._validate_pdf_file(pdf_path)
            
            logger.info(f"Start processing PDF file: {pdf_path}")
            
            # 1. Parse PDF structure
            pdf_data = self.pdf_processor.process(pdf_path)
            
            # 2. Process each page
            pages = self._process_pages(pdf_data)
            
            # 3. Merge results
            result = self._merge_results(pages, pdf_data.metadata)
            
            # 4. Post-process
            if self.text_processor:
                result = self.text_processor.post_process(result)
            
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            
            logger.info(f"PDF processing completed, time used: {processing_time:.2f} seconds")
            
            return result
            
        except (PDFNotFoundError, PDFCorruptedError, PDFPasswordProtectedError, OCRError, LayoutDetectionError, TableExtractionError, ImageProcessingError, ConfigurationError, ValidationError, UnsupportedFormatError, ProcessingTimeoutError) as e:
            # Re-raise specific exceptions as-is
            raise
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            raise SmartExtractorError(f"PDF processing failed: {e}")
    
    def extract_pages(self, pdf_path: str) -> List[PageResult]:
        """
        Extract PDF content by page
        
        Args:
            pdf_path: PDF file path
            
        Returns:
            List of extraction results for each page
        """
        try:
            self._validate_pdf_file(pdf_path)
            
            pdf_data = self.pdf_processor.process(pdf_path)
            return self._process_pages(pdf_data)
            
        except (PDFNotFoundError, PDFCorruptedError, PDFPasswordProtectedError, OCRError, LayoutDetectionError, TableExtractionError, ImageProcessingError, ConfigurationError, ValidationError, UnsupportedFormatError, ProcessingTimeoutError) as e:
            # Re-raise specific exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Page extraction failed: {e}")
            raise SmartExtractorError(f"Page extraction failed: {e}")
    
    def _validate_pdf_file(self, pdf_path: str):
        """Validate PDF file"""
        if not os.path.exists(pdf_path):
            raise PDFNotFoundError(f"PDF file does not exist: {pdf_path}")
        
        if not pdf_path.lower().endswith('.pdf'):
            raise SmartExtractorError(f"File is not a PDF: {pdf_path}")
        
        # Check file size
        file_size = os.path.getsize(pdf_path)
        if file_size == 0:
            raise PDFCorruptedError(f"PDF file is empty: {pdf_path}")
    
    def _process_pages(self, pdf_data) -> List[PageResult]:
        """Process all pages"""
        pages = []
        
        if self.config.max_workers > 1:
            # Multi-threaded processing
            pages = self._process_pages_parallel(pdf_data)
        else:
            # Single-threaded processing
            pages = self._process_pages_sequential(pdf_data)
        
        return pages
    
    def _process_pages_sequential(self, pdf_data) -> List[PageResult]:
        """Process pages sequentially"""
        pages = []
        
        for page_num, page_data in enumerate(pdf_data.pages, 1):
            try:
                logger.info(f"Processing page {page_num}")
                page_result = self._process_single_page(page_data, page_num)
                pages.append(page_result)
                
            except Exception as e:
                logger.error(f"Failed to process page {page_num}: {e}")
                # Create empty page result
                pages.append(PageResult(page_number=page_num))
        
        return pages
    
    def _process_pages_parallel(self, pdf_data) -> List[PageResult]:
        """Process pages in parallel"""
        pages = [None] * len(pdf_data.pages)
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit tasks
            future_to_page = {
                executor.submit(self._process_single_page, page_data, page_num): page_num - 1
                for page_num, page_data in enumerate(pdf_data.pages, 1)
            }
            
            # Collect results
            for future in as_completed(future_to_page):
                page_index = future_to_page[future]
                try:
                    page_result = future.result()
                    pages[page_index] = page_result
                except Exception as e:
                    logger.error(f"Failed to process page: {e}")
                    pages[page_index] = PageResult(page_number=page_index + 1)
        
        return pages
    
    def _process_single_page(self, page_data, page_num: int) -> PageResult:
        """Process a single page"""
        page_result = PageResult(page_number=page_num)
        
        try:
            # 1. Extract text blocks
            text_blocks = self._extract_text_blocks(page_data)
            page_result.text_blocks = text_blocks
            
            # 2. Layout detection
            if self.layout_processor:
                page_result = self.layout_processor.process(page_result, page_data)
            
            # 3. Table detection and extraction
            if self.table_processor:
                tables = self.table_processor.extract_tables(page_data, page_num)
                page_result.tables = tables
            
            # 4. Image processing
            if self.image_processor:
                images = self.image_processor.extract_images(page_data, page_num)
                page_result.images = images
            
            # 5. OCR processing (if needed)
            if self.ocr_processor and self._needs_ocr(page_data):
                ocr_blocks = self.ocr_processor.process_page(page_data, page_num)
                page_result.text_blocks.extend(ocr_blocks)
            
            # Set page size
            page_result.width = page_data.width
            page_result.height = page_data.height
            
        except Exception as e:
            logger.error(f"Error processing page {page_num}: {e}")
            # Return basic page result
        
        return page_result
    
    def _extract_text_blocks(self, page_data) -> List[TextBlock]:
        """Extract text blocks"""
        text_blocks = []
        
        try:
            # Extract text from PDF
            for text_obj in page_data.text_objects:
                block = TextBlock(
                    text=text_obj.text,
                    bbox=text_obj.bbox,
                    font_size=text_obj.font_size,
                    font_family=text_obj.font_family,
                    is_bold=text_obj.is_bold,
                    is_italic=text_obj.is_italic
                )
                text_blocks.append(block)
                
        except Exception as e:
            logger.warning(f"Error extracting text blocks: {e}")
        
        return text_blocks
    
    def _needs_ocr(self, page_data) -> bool:
        """Determine if OCR is needed"""
        # If there are no text objects or very little text, OCR may be needed
        if not page_data.text_objects:
            return True
        
        # Check text coverage
        total_text_length = sum(len(obj.text) for obj in page_data.text_objects)
        if total_text_length < 50:  # Too little text, OCR may be needed
            return True
        
        return False
    
    def _merge_results(self, pages: List[PageResult], metadata: Dict[str, Any]) -> ExtractionResult:
        """Merge results from all pages"""
        # Merge text
        all_text = "\n\n".join(page.text for page in pages if page.text)
        
        # Merge tables
        all_tables = []
        for page in pages:
            all_tables.extend(page.tables)
        
        # Merge images
        all_images = []
        for page in pages:
            all_images.extend(page.images)
        
        return ExtractionResult(
            text=all_text,
            pages=pages,
            tables=all_tables,
            images=all_images,
            metadata=metadata
        )
    
    def get_supported_languages(self) -> List[str]:
        """Get supported languages"""
        if self.ocr_processor:
            return self.ocr_processor.get_supported_languages()
        return []
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            "ocr_enabled": self.config.enable_ocr,
            "layout_detection_enabled": self.config.enable_layout_detection,
            "table_extraction_enabled": self.config.enable_table_extraction,
            "image_processing_enabled": self.config.enable_image_processing,
            "text_cleaning_enabled": self.config.enable_text_cleaning,
            "max_workers": self.config.max_workers,
            "supported_languages": self.get_supported_languages()
        } 