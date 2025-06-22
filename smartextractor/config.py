"""
Configuration Module - Define SmartExtractor configuration options
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ExtractionConfig:
    """PDF Text Extraction Configuration Class"""
    
    # OCR related configuration
    enable_ocr: bool = True
    ocr_engine: str = "auto"  # "tesseract", "easyocr", "auto"
    language: str = "zh-CN"
    confidence_threshold: float = 0.8
    
    # Layout detection configuration
    enable_layout_detection: bool = True
    detect_headers: bool = True
    detect_footers: bool = True
    detect_columns: bool = True
    
    # Table extraction configuration
    enable_table_extraction: bool = True
    table_detection_method: str = "auto"  # "image", "structure", "auto"
    
    # Image processing configuration
    enable_image_processing: bool = True
    image_quality: int = 200  # DPI
    image_format: str = "PNG"
    
    # Text processing configuration
    enable_text_cleaning: bool = True
    remove_headers_footers: bool = True
    merge_hyphenated_words: bool = True
    fix_encoding: bool = True
    
    # Performance configuration
    max_workers: int = 4
    chunk_size: int = 10  # Number of pages processed per batch
    timeout: int = 300  # Timeout in seconds
    
    # Output configuration
    output_format: str = "text"  # "text", "json", "structured"
    include_metadata: bool = True
    include_images: bool = False
    
    # Advanced configuration
    custom_ocr_config: Dict[str, Any] = field(default_factory=dict)
    layout_model_path: Optional[str] = None
    table_model_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration parameters"""
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        
        if self.ocr_engine not in ["tesseract", "easyocr", "auto"]:
            raise ValueError("ocr_engine must be 'tesseract', 'easyocr' or 'auto'")
        
        if self.table_detection_method not in ["image", "structure", "auto"]:
            raise ValueError("table_detection_method must be 'image', 'structure' or 'auto'")
        
        if self.output_format not in ["text", "json", "structured"]:
            raise ValueError("output_format must be 'text', 'json' or 'structured'")
        
        if self.max_workers < 1:
            raise ValueError("max_workers must be greater than 0")
        
        if self.chunk_size < 1:
            raise ValueError("chunk_size must be greater than 0")
        
        if self.timeout < 1:
            raise ValueError("timeout must be greater than 0")


@dataclass
class OCRConfig:
    """OCR Engine Configuration"""
    
    engine: str = "tesseract"
    language: str = "chi_sim+eng"
    config: str = "--psm 6"
    timeout: int = 30
    dpi: int = 300
    
    # EasyOCR specific configuration
    easyocr_gpu: bool = False
    easyocr_model_path: Optional[str] = None
    
    # Tesseract specific configuration
    tesseract_path: Optional[str] = None
    tesseract_config: Dict[str, str] = field(default_factory=dict)


@dataclass
class LayoutConfig:
    """Layout Detection Configuration"""
    
    detect_headers: bool = True
    detect_footers: bool = True
    detect_columns: bool = True
    detect_lists: bool = True
    detect_tables: bool = True
    
    # Detection parameters
    header_threshold: float = 0.1  # Top page ratio
    footer_threshold: float = 0.1  # Bottom page ratio
    column_gap_threshold: float = 50  # Column gap threshold (pixels)
    
    # Model configuration
    model_path: Optional[str] = None
    confidence_threshold: float = 0.7


@dataclass
class TableConfig:
    """Table Extraction Configuration"""
    
    detection_method: str = "auto"  # "image", "structure", "auto"
    min_cells: int = 4  # Minimum number of cells
    min_rows: int = 2   # Minimum number of rows
    min_cols: int = 2   # Minimum number of columns
    
    # Structure detection parameters
    line_threshold: float = 0.8
    cell_padding: int = 5
    
    # Image detection parameters
    table_confidence_threshold: float = 0.7
    table_model_path: Optional[str] = None
    
    # Output format
    output_format: str = "pandas"  # "pandas", "dict", "csv" 