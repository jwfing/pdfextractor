"""
Data Models - Define data structures for extraction results
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json


@dataclass
class TextBlock:
    """Text block"""
    
    text: str
    bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float = 1.0
    font_size: Optional[float] = None
    font_family: Optional[str] = None
    is_bold: bool = False
    is_italic: bool = False
    block_type: str = "text"  # "text", "title", "header", "footer"


@dataclass
class TableCell:
    """Table cell"""
    
    text: str
    row: int
    col: int
    bbox: List[float]
    confidence: float = 1.0
    is_header: bool = False


@dataclass
class TableResult:
    """Table extraction result"""
    
    cells: List[TableCell]
    rows: int
    cols: int
    bbox: List[float]
    confidence: float = 1.0
    page_number: int = 0
    
    def to_dataframe(self):
        """Convert to pandas DataFrame"""
        try:
            import pandas as pd
            
            # Create 2D array
            data = [['' for _ in range(self.cols)] for _ in range(self.rows)]
            
            for cell in self.cells:
                if 0 <= cell.row < self.rows and 0 <= cell.col < self.cols:
                    data[cell.row][cell.col] = cell.text
            
            return pd.DataFrame(data)
        except ImportError:
            raise ImportError("pandas not installed, cannot convert to DataFrame")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "rows": self.rows,
            "cols": self.cols,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "page_number": self.page_number,
            "cells": [
                {
                    "text": cell.text,
                    "row": cell.row,
                    "col": cell.col,
                    "bbox": cell.bbox,
                    "confidence": cell.confidence,
                    "is_header": cell.is_header
                }
                for cell in self.cells
            ]
        }


@dataclass
class ImageResult:
    """Image extraction result"""
    
    image_path: str
    bbox: List[float]
    page_number: int
    image_type: str = "image"  # "image", "chart", "diagram"
    extracted_text: Optional[str] = None
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "image_path": self.image_path,
            "bbox": self.bbox,
            "page_number": self.page_number,
            "image_type": self.image_type,
            "extracted_text": self.extracted_text,
            "confidence": self.confidence
        }


@dataclass
class PageResult:
    """Single page extraction result"""
    
    page_number: int
    text_blocks: List[TextBlock] = field(default_factory=list)
    tables: List[TableResult] = field(default_factory=list)
    images: List[ImageResult] = field(default_factory=list)
    width: float = 0.0
    height: float = 0.0
    
    @property
    def text(self) -> str:
        """Get page text"""
        return "\n".join(block.text for block in self.text_blocks)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "text_blocks": [
                {
                    "text": block.text,
                    "bbox": block.bbox,
                    "confidence": block.confidence,
                    "font_size": block.font_size,
                    "font_family": block.font_family,
                    "is_bold": block.is_bold,
                    "is_italic": block.is_italic,
                    "block_type": block.block_type
                }
                for block in self.text_blocks
            ],
            "tables": [table.to_dict() for table in self.tables],
            "images": [image.to_dict() for image in self.images]
        }


@dataclass
class ExtractionResult:
    """Complete extraction result"""
    
    text: str
    pages: List[PageResult] = field(default_factory=list)
    tables: List[TableResult] = field(default_factory=list)
    images: List[ImageResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    extraction_date: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-initialization processing"""
        # If text is not provided, extract from pages
        if not self.text and self.pages:
            self.text = "\n\n".join(page.text for page in self.pages)
        
        # If tables are not provided, extract from pages
        if not self.tables and self.pages:
            self.tables = []
            for page in self.pages:
                self.tables.extend(page.tables)
        
        # If images are not provided, extract from pages
        if not self.images and self.pages:
            self.images = []
            for page in self.pages:
                self.images.extend(page.images)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "text": self.text,
            "pages": [page.to_dict() for page in self.pages],
            "tables": [table.to_dict() for table in self.tables],
            "images": [image.to_dict() for image in self.images],
            "metadata": self.metadata,
            "processing_time": self.processing_time,
            "extraction_date": self.extraction_date.isoformat()
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON format"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def save_json(self, file_path: str, indent: int = 2):
        """Save as JSON file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=indent, ensure_ascii=False)
    
    def save_text(self, file_path: str):
        """Save as text file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.text)
    
    def get_table_dataframes(self):
        """Get list of DataFrames for all tables"""
        return [table.to_dataframe() for table in self.tables]
    
    def get_text_by_type(self, block_type: str) -> str:
        """Get text by block type"""
        texts = []
        for page in self.pages:
            for block in page.text_blocks:
                if block.block_type == block_type:
                    texts.append(block.text)
        return "\n".join(texts)
    
    def get_tables_by_page(self, page_number: int) -> List[TableResult]:
        """Get tables from specified page"""
        for page in self.pages:
            if page.page_number == page_number:
                return page.tables
        return []
    
    def get_images_by_page(self, page_number: int) -> List[ImageResult]:
        """Get images from specified page"""
        for page in self.pages:
            if page.page_number == page_number:
                return page.images
        return [] 