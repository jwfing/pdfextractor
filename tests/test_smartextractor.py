"""
SmartExtractor Tests
"""
import logging

import pytest
from pathlib import Path

from smartextractor import SmartExtractor, ExtractionConfig
from smartextractor.exceptions import PDFNotFoundError

logger = logging.getLogger(__name__)

class TestSmartExtractor:
    """SmartExtractor Test Class"""
    
    def test_init_default_config(self):
        """Test default config initialization"""
        extractor = SmartExtractor()
        assert extractor.config is not None
        assert extractor.config.enable_ocr is True
        assert extractor.config.language == "zh-CN"
    
    def test_init_custom_config(self):
        """Test custom config initialization"""
        config = ExtractionConfig(
            enable_ocr=False,
            language="en",
            confidence_threshold=0.9
        )
        extractor = SmartExtractor(config)
        assert extractor.config.enable_ocr is False
        assert extractor.config.language == "en"
        assert extractor.config.confidence_threshold == 0.9
    
    def test_invalid_config(self):
        """Test invalid config"""
        with pytest.raises(ValueError):
            ExtractionConfig(confidence_threshold=1.5)
        
        with pytest.raises(ValueError):
            ExtractionConfig(ocr_engine="invalid")
    
    def test_nonexistent_pdf(self):
        """Test nonexistent PDF file"""
        extractor = SmartExtractor()
        with pytest.raises(PDFNotFoundError):
            extractor.extract_text("nonexistent.pdf")
    
    def test_get_processing_stats(self):
        """Test get processing stats"""
        extractor = SmartExtractor()
        stats = extractor.get_processing_stats()
        
        assert "ocr_enabled" in stats
        assert "layout_detection_enabled" in stats
        assert "table_extraction_enabled" in stats
        assert "supported_languages" in stats
    
    def test_get_supported_languages(self):
        """Test get supported languages"""
        extractor = SmartExtractor()
        languages = extractor.get_supported_languages()
        assert isinstance(languages, list)

    def test_two_columns_pdf(self):
        config = ExtractionConfig(
            enable_ocr=False,
            enable_layout_detection=True,
            language="en",
            confidence_threshold=0.1,
            remove_headers_footers=True
        )
        extractor = SmartExtractor(config)
        pdf_file = "./examples/patent22.pdf"
        context = extractor.extract_text(str(pdf_file))
        logger.info(f"{pdf_file} read result: {context}")
        print(f"{pdf_file} read result: {context}")
        assert len(context) > 0
        assert "BATTERY WITH MULTIPLE JELLY ROLLS of conductive tabs extend through seals in the pouch to" not in context
        assert "This application is a continuation of, and hereby claims In some embodiments" not in context


    def test_single_column_pdf(self):
        config = ExtractionConfig(
            enable_ocr=False,
            enable_layout_detection=True,
            enable_image_processing=False,
            language="en",
            confidence_threshold=0.1,
            remove_headers_footers=True
        )
        extractor = SmartExtractor(config)
        pdf_file = "./examples/Asset Purchase Agreement, dated as of April 22, 2021, by and _ Skyworks Solutions _ Business Contracts _ Justia.pdf"
        context = extractor.extract_text(str(pdf_file))
        logger.info(f"{pdf_file} read result: {context}")
        print(f"{pdf_file} read result: {context}")
        assert len(context) > 0


    def test_read_pdf_file(self):
        """Test custom config initialization"""
        config = ExtractionConfig(
            enable_ocr=True,
            enable_layout_detection=True,
            language="en",
            confidence_threshold=0.8
        )
        extractor = SmartExtractor(config)
        user_files_dir = Path(__file__).parent.parent / "examples"
        # 查找目录中所有的 PDF 文件
        pdf_files = list(user_files_dir.glob("*.pdf"))
        assert len(pdf_files) > 0, f"No PDF files found in {user_files_dir}"

        logger.info(f"\nFound {len(pdf_files)} PDF files to test.")

        for pdf_file in pdf_files:
            context = extractor.extract_text(str(pdf_file))
            logger.info(f"\t{pdf_file}: {context}")
            assert len(context) > 0


class TestExtractionConfig:
    """ExtractionConfig Test Class"""
    
    def test_default_values(self):
        """Test default values"""
        config = ExtractionConfig()
        
        assert config.enable_ocr is True
        assert config.enable_layout_detection is True
        assert config.enable_table_extraction is True
        assert config.language == "zh-CN"
        assert config.confidence_threshold == 0.8
        assert config.max_workers == 4
    
    def test_custom_values(self):
        """Test custom values"""
        config = ExtractionConfig(
            enable_ocr=False,
            enable_layout_detection=False,
            language="en",
            confidence_threshold=0.9,
            max_workers=8
        )
        
        assert config.enable_ocr is False
        assert config.enable_layout_detection is False
        assert config.language == "en"
        assert config.confidence_threshold == 0.9
        assert config.max_workers == 8


class TestModels:
    """Data Models Test Class"""
    
    def test_text_block(self):
        """Test TextBlock"""
        from smartextractor.models import TextBlock
        
        block = TextBlock(
            text="Test text",
            bbox=[0, 0, 100, 50],
            font_size=12.0,
            is_bold=True
        )
        
        assert block.text == "Test text"
        assert block.bbox == [0, 0, 100, 50]
        assert block.font_size == 12.0
        assert block.is_bold is True
        assert block.is_italic is False
    
    def test_table_result(self):
        """Test TableResult"""
        from smartextractor.models import TableResult, TableCell
        
        cells = [
            TableCell(text="Header1", row=0, col=0, bbox=[0, 0, 50, 20]),
            TableCell(text="Header2", row=0, col=1, bbox=[50, 0, 100, 20]),
            TableCell(text="Data1", row=1, col=0, bbox=[0, 20, 50, 40]),
            TableCell(text="Data2", row=1, col=1, bbox=[50, 20, 100, 40])
        ]
        
        table = TableResult(
            cells=cells,
            rows=2,
            cols=2,
            bbox=[0, 0, 100, 40]
        )
        
        assert table.rows == 2
        assert table.cols == 2
        assert len(table.cells) == 4
        
        # Test conversion to dict
        table_dict = table.to_dict()
        assert "rows" in table_dict
        assert "cols" in table_dict
        assert "cells" in table_dict 