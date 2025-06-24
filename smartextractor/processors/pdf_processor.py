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
                    if pdf.pages:
                        page_num = 0
                        page = pdf.pages[0]
                    # for page_num, page in enumerate(pdf.pages, 1):
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
            if not chars:
                # If no character information, try to extract text
                text = page.extract_text()
                if text:
                    text_objects.append(TextObject(
                        text=text,
                        bbox=[0, 0, page.width, page.height]
                    ))
                return text_objects
            # Group characters by font and position (一行一组)
            char_groups = self._group_chars_by_font(chars)
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
                    # 检查是否为超宽文本块（疑似跨两栏）
                    block_width = bbox[2] - bbox[0]
                    if block_width > page.width * 0.60 and len(col_group) > 10:
                        # 尝试用 x 坐标聚类分成两栏
                        xs = [char['x0'] for char in col_group]
                        from sklearn.cluster import KMeans
                        import numpy as np
                        X = np.array(xs).reshape(-1, 1)
                        try:
                            kmeans = KMeans(n_clusters=2, random_state=0).fit(X)
                            labels = kmeans.labels_
                            left_chars = [char for char, label in zip(col_group, labels) if label == 0]
                            right_chars = [char for char, label in zip(col_group, labels) if label == 1]
                            # 按 x 坐标均值排序
                            left_mean = np.mean([char['x0'] for char in left_chars]) if left_chars else 0
                            right_mean = np.mean([char['x0'] for char in right_chars]) if right_chars else 0
                            if left_mean > right_mean:
                                left_chars, right_chars = right_chars, left_chars
                            # 生成两个小块
                            for sub_chars in [left_chars, right_chars]:
                                if len(sub_chars) < 3:
                                    continue
                                sub_text = ''.join(char['text'] for char in sub_chars)
                                sub_bbox = self._calculate_bbox(sub_chars)
                                sub_font_info = self._extract_font_info(sub_chars[0])
                                text_objects.append(TextObject(
                                    text=sub_text,
                                    bbox=sub_bbox,
                                    font_size=sub_font_info.get('size'),
                                    font_family=sub_font_info.get('fontname'),
                                    is_bold=sub_font_info.get('is_bold', False),
                                    is_italic=sub_font_info.get('is_italic', False)
                                ))
                            continue  # 跳过原始大块
                        except Exception as e:
                            logger.warning(f"[SPLIT] KMeans split failed: {e}")
                    # 正常情况
                    text_objects.append(TextObject(
                        text=text,
                        bbox=bbox,
                        font_size=font_info.get('size'),
                        font_family=font_info.get('fontname'),
                        is_bold=font_info.get('is_bold', False),
                        is_italic=font_info.get('is_italic', False)
                    ))
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
    
    def _split_line_by_columns(self, chars: list, page_width: float, min_gap_ratio: float = 0.15) -> list:
        """将一行字符按 x 坐标分割为多列，适配多栏文档。min_gap_ratio 表示多大间隔才认为是分栏。"""
        if not chars:
            return []
        
        # 按 x0 升序排列
        chars = sorted(chars, key=lambda c: c.get('x0', 0))
        
        # 如果字符数量很少，不需要分割
        if len(chars) <= 3:
            return [chars]
        
        # 计算所有字符之间的间隔
        gaps = []
        for i in range(1, len(chars)):
            prev_x1 = chars[i-1].get('x1', 0)
            curr_x0 = chars[i].get('x0', 0)
            gaps.append(curr_x0 - prev_x1)
        
        # 统计大间隔
        min_gap = page_width * min_gap_ratio  # 比如 A4 宽度 600，0.15=90pt
        
        # 找到所有大间隔的位置
        large_gaps = []
        for idx, gap in enumerate(gaps):
            if gap > min_gap:
                large_gaps.append((idx, gap))
        
        # 添加调试信息
        if len(chars) > 10:  # 只对较长的行进行调试
            text = ''.join(char['text'] for char in chars)

        # 如果没有大间隔，或者只有一个大间隔但间隔不够大，就不分割
        if not large_gaps:
            return [chars]
        
        # 如果只有一个大间隔，需要更严格的判断
        if len(large_gaps) == 1:
            gap_idx, gap_size = large_gaps[0]
            # 如果间隔不够大（小于页面宽度的20%），或者分割后的文本块太小，就不分割
            if gap_size < page_width * 0.20:
                return [chars]
            
            # 检查分割后的文本块大小
            left_chars = chars[:gap_idx+1]
            right_chars = chars[gap_idx+1:]
            
            # 如果任一边的字符太少（少于2个），就不分割
            if len(left_chars) < 2 or len(right_chars) < 2:
                return [chars]
            
            # 检查分割后的文本内容是否合理
            left_text = ''.join(char['text'] for char in left_chars).strip()
            right_text = ''.join(char['text'] for char in right_chars).strip()
            
            # 如果任一边的文本太短（少于3个字符），就不分割
            if len(left_text) < 3 or len(right_text) < 3:
                return [chars]
            
            # 如果分割后的文本看起来像是一个完整的句子被错误分割，就不分割
            # 检查是否包含常见的句子连接词
            combined_text = left_text + ' ' + right_text
            if any(connector in combined_text.lower() for connector in ['and', 'or', 'but', 'however', 'therefore', 'thus', 'hence']):
                # 如果包含连接词，可能是被错误分割的句子
                if len(combined_text) < 100:  # 如果合并后的文本不太长，就不分割
                    return [chars]
        
        # 执行分割
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
        
        result = [g for g in column_groups if g]
        
        return result
    
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