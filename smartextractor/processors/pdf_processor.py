"""
PDF Processor - Responsible for parsing PDF file structure
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import PyPDF2
import pdfplumber
from loguru import logger

from ..config import ExtractionConfig
from ..exceptions import PDFProcessingError, PDFCorruptedError, PDFPasswordProtectedError


@dataclass
class TextObject:
    """Text object"""
    text: str
    bbox: List[float]  # [x1, y1, x2, y2]
    font_size: Optional[float] = None
    font_family: Optional[str] = None
    is_bold: bool = False
    is_italic: bool = False


@dataclass
class PageData:
    """Page data"""
    page_number: int
    width: float
    height: float
    text_objects: List[TextObject]
    images: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]


@dataclass
class PDFData:
    """PDF data"""
    pages: List[PageData]
    metadata: Dict[str, Any]
    num_pages: int
    is_encrypted: bool


class PDFProcessor:
    """PDF Processor"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
    
    def process(self, pdf_path: str) -> PDFData:
        """
        Process PDF file
        
        Args:
            pdf_path: PDF file path
            
        Returns:
            PDF data object
        """
        try:
            logger.info(f"Start parsing PDF file: {pdf_path}")
            
            # Check if file exists
            if not os.path.exists(pdf_path):
                raise PDFProcessingError(f"PDF file does not exist: {pdf_path}")
            
            # Use pdfplumber to parse PDF
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    # Extract metadata
                    metadata = self._extract_metadata(pdf)
                    
                    # Process each page
                    pages = []
                    for page_num, page in enumerate(pdf.pages, 1):
                        try:
                            page_data = self._process_page(page, page_num)
                            pages.append(page_data)
                        except Exception as e:
                            logger.warning(f"Error processing page {page_num}: {e}")
                            # Create empty page data
                            pages.append(self._create_empty_page(page_num))
                    
                    return PDFData(
                        pages=pages,
                        metadata=metadata,
                        num_pages=len(pages),
                        is_encrypted=False
                    )
            except Exception as pdf_error:
                # Check if it's an encryption error
                if "password" in str(pdf_error).lower() or "encrypted" in str(pdf_error).lower():
                    raise PDFPasswordProtectedError("PDF file is encrypted")
                else:
                    raise pdf_error
                
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            raise PDFProcessingError(f"PDF processing failed: {e}")
    
    def _extract_metadata(self, pdf) -> Dict[str, Any]:
        """Extract PDF metadata"""
        metadata = {}
        
        try:
            if pdf.metadata:
                metadata.update(pdf.metadata)
            
            # Add basic information
            metadata.update({
                "num_pages": len(pdf.pages),
                "file_size": os.path.getsize(pdf.stream.name) if hasattr(pdf.stream, 'name') else 0,
            })
            
        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")
        
        return metadata
    
    def _process_page(self, page, page_num: int) -> PageData:
        """Process single page"""
        try:
            # Get page dimensions
            width = page.width
            height = page.height
            
            # Extract text objects
            text_objects = self._extract_text_objects(page)
            
            # Extract images
            images = self._extract_images(page)
            
            # Extract tables
            tables = self._extract_tables(page)
            
            return PageData(
                page_number=page_num,
                width=width,
                height=height,
                text_objects=text_objects,
                images=images,
                tables=tables
            )
            
        except Exception as e:
            logger.error(f"Error processing page {page_num}: {e}")
            return self._create_empty_page(page_num)
    
    def _extract_text_objects(self, page) -> List[TextObject]:
        """Extract text objects"""
        text_objects = []
        try:
            # Use pdfplumber to extract text blocks
            chars = page.chars
            logger.info(f"Found {len(chars) if chars else 0} characters on page")
            if not chars:
                # If no character information, try to extract text
                text = page.extract_text()
                logger.info(f"Extracted text using extract_text(): {text[:200] if text else 'None'}")
                if text:
                    text_objects.append(TextObject(
                        text=text,
                        bbox=[0, 0, page.width, page.height]
                    ))
                return text_objects
            # Group characters by font and position (一行一组)
            char_groups = self._group_chars_by_font(chars)
            logger.info(f"Grouped into {len(char_groups)} character groups")
            # 对每一行再按 x 坐标分割，适配多栏
            for i, group in enumerate(char_groups):
                if not group:
                    continue
                # 按 x 坐标分割为多列
                column_groups = self._split_line_by_columns(group, page.width)
                for col_idx, col_group in enumerate(column_groups):
                    text = ''.join(char['text'] for char in col_group)
                    if not text.strip():
                        continue
                    bbox = self._calculate_bbox(col_group)
                    font_info = self._extract_font_info(col_group[0])
                    text_objects.append(TextObject(
                        text=text,
                        bbox=bbox,
                        font_size=font_info.get('size'),
                        font_family=font_info.get('fontname'),
                        is_bold=font_info.get('is_bold', False),
                        is_italic=font_info.get('is_italic', False)
                    ))
                    if i < 3 and col_idx < 2:  # 只打印前几组调试
                        logger.info(f"Text object {i}-{col_idx}: '{text[:50]}...' at bbox {bbox}")
            logger.info(f"Created {len(text_objects)} text objects")
        except Exception as e:
            logger.warning(f"Error extracting text objects: {e}")
        return text_objects
    
    def _group_chars_by_font(self, chars) -> List[List[Dict]]:
        """Group characters by font"""
        groups = []
        current_group = []
        current_font = None
        
        for char in chars:
            font_key = (
                char.get('fontname', ''),
                char.get('size', 0),
                char.get('top', 0)  # Group by line
            )
            
            if current_font != font_key and current_group:
                groups.append(current_group)
                current_group = []
            
            current_font = font_key
            current_group.append(char)
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _calculate_bbox(self, chars: List[Dict]) -> List[float]:
        """Calculate bounding box for character group"""
        if not chars:
            return [0, 0, 0, 0]
        
        x0 = min(char.get('x0', 0) for char in chars)
        y0 = min(char.get('top', 0) for char in chars)
        x1 = max(char.get('x1', 0) for char in chars)
        y1 = max(char.get('bottom', 0) for char in chars)
        
        return [x0, y0, x1, y1]
    
    def _extract_font_info(self, char: Dict) -> Dict[str, Any]:
        """Extract font information"""
        font_info = {
            'size': char.get('size'),
            'fontname': char.get('fontname'),
            'is_bold': False,
            'is_italic': False
        }
        
        # Simple font style detection
        fontname = char.get('fontname', '').lower()
        if 'bold' in fontname:
            font_info['is_bold'] = True
        if 'italic' in fontname or 'oblique' in fontname:
            font_info['is_italic'] = True
        
        return font_info
    
    def _extract_images(self, page) -> List[Dict[str, Any]]:
        """Extract image information"""
        images = []
        
        try:
            # Use pdfplumber to extract images
            for image in page.images:
                images.append({
                    'bbox': [image['x0'], image['y0'], image['x1'], image['y1']],
                    'width': image['width'],
                    'height': image['height'],
                    'type': image.get('name', 'image')
                })
                
        except Exception as e:
            logger.warning(f"Error extracting images: {e}")
        
        return images
    
    def _extract_tables(self, page) -> List[Dict[str, Any]]:
        """Extract table information"""
        tables = []
        
        try:
            # Use pdfplumber to extract tables
            extracted_tables = page.extract_tables()
            
            for table in extracted_tables:
                if table and len(table) > 0:
                    tables.append({
                        'data': table,
                        'rows': len(table),
                        'cols': len(table[0]) if table[0] else 0
                    })
                    
        except Exception as e:
            logger.warning(f"Error extracting tables: {e}")
        
        return tables
    
    def _split_line_by_columns(self, chars: list, page_width: float, min_gap_ratio: float = 0.12) -> list:
        """将一行字符按 x 坐标分割为多列，适配多栏文档。min_gap_ratio 表示多大间隔才认为是分栏。"""
        if not chars:
            return []
        # 按 x0 升序排列
        chars = sorted(chars, key=lambda c: c.get('x0', 0))
        # 计算所有字符之间的间隔
        gaps = []
        for i in range(1, len(chars)):
            prev_x1 = chars[i-1].get('x1', 0)
            curr_x0 = chars[i].get('x0', 0)
            gaps.append(curr_x0 - prev_x1)
        # 统计大间隔
        min_gap = page_width * min_gap_ratio  # 比如 A4 宽度 600，0.12=72pt
        split_indices = [0]
        for idx, gap in enumerate(gaps):
            if gap > min_gap:
                split_indices.append(idx+1)
        split_indices.append(len(chars))
        # 按分割点切分
        column_groups = []
        for i in range(len(split_indices)-1):
            start = split_indices[i]
            end = split_indices[i+1]
            column_groups.append(chars[start:end])
        return [g for g in column_groups if g]
    
    def _create_empty_page(self, page_num: int) -> PageData:
        """Create empty page data"""
        return PageData(
            page_number=page_num,
            width=0,
            height=0,
            text_objects=[],
            images=[],
            tables=[]
        ) 