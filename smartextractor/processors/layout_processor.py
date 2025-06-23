"""
Layout Processor - Responsible for detecting document layout structure
"""

from typing import List, Tuple, Dict
from loguru import logger

from ..config import ExtractionConfig
from ..models import PageResult, TextBlock
from ..exceptions import LayoutDetectionError


class LayoutProcessor:
    """Layout Processor"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
    
    def process(self, page_result: PageResult, page_data) -> PageResult:
        """Process page layout"""
        try:
            logger.info(f"Layout detection for page {page_result.page_number}")
            
            # Detect titles
            if self.config.detect_headers:
                page_result = self._detect_headers(page_result)
            
            # Detect headers and footers
            if self.config.detect_headers:
                page_result = self._detect_headers_footers(page_result)
            
            # Detect multi-column layout
            if self.config.detect_columns:
                page_result = self._detect_columns(page_result)
            
            return page_result
            
        except Exception as e:
            logger.error(f"Layout detection failed: {e}")
            raise LayoutDetectionError(f"Layout detection failed: {e}")
    
    def _detect_headers(self, page_result: PageResult) -> PageResult:
        """Detect titles"""
        # Detect titles based on font size and position
        for block in page_result.text_blocks:
            if block.font_size and block.font_size > 14:  # Simple size threshold
                block.block_type = "title"
        
        return page_result
    
    def _detect_headers_footers(self, page_result: PageResult) -> PageResult:
        """Detect headers and footers with improved accuracy"""
        page_height = page_result.height
        page_width = page_result.width
        
        # More conservative thresholds (5% instead of 10%)
        header_threshold = page_height * 0.05
        footer_threshold = page_height * 0.95
        
        for block in page_result.text_blocks:
            if not block.bbox or len(block.bbox) < 4:
                continue
                
            y_top = block.bbox[1]
            y_bottom = block.bbox[3]
            x_left = block.bbox[0]
            x_right = block.bbox[2]
            
            # Calculate text block dimensions
            block_height = y_bottom - y_top
            block_width = x_right - x_left
            
            # Skip very large text blocks (likely main content)
            if block_height > page_height * 0.3 or block_width > page_width * 0.8:
                continue
            
            # Header detection: text block must be mostly in top 5% area
            if y_top < header_threshold and y_bottom < header_threshold * 2:
                # Additional content-based checks for headers
                if self._is_likely_header(block, page_width):
                    block.block_type = "header"
            
            # Footer detection: text block must be mostly in bottom 5% area
            elif y_bottom > footer_threshold and y_top > footer_threshold - header_threshold:
                # Additional content-based checks for footers
                if self._is_likely_footer(block, page_width):
                    block.block_type = "footer"
        
        return page_result
    
    def _is_likely_header(self, block: TextBlock, page_width: float) -> bool:
        """Check if text block is likely a header based on content characteristics"""
        if not block.text:
            return False
        
        text = block.text.strip()
        
        # Skip empty or very short text
        if len(text) < 2:
            return False
        
        # Skip very long text (likely main content)
        if len(text) > 200:
            return False
        
        # Check for typical header patterns
        header_patterns = [
            # Page numbers
            r'^\d+$',
            # Document titles (short, centered)
            r'^[A-Z][A-Z\s]{1,50}$',
            # Chapter/section headers
            r'^(Chapter|Section|Part)\s+\d+',
            # Date patterns
            r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$',
            r'^\d{4}-\d{2}-\d{2}$',
            # Company/organization names (short)
            r'^[A-Z][A-Z\s&]{1,30}$'
        ]
        
        import re
        for pattern in header_patterns:
            if re.match(pattern, text):
                return True
        
        # Check if text is centered (typical for headers)
        if block.bbox and len(block.bbox) >= 4:
            block_center = (block.bbox[0] + block.bbox[2]) / 2
            page_center = page_width / 2
            # Allow some tolerance for centering
            if abs(block_center - page_center) < page_width * 0.1:
                return True
        
        # Check font size (headers often have smaller font)
        if block.font_size and block.font_size < 12:
            return True
        
        return False
    
    def _is_likely_footer(self, block: TextBlock, page_width: float) -> bool:
        """Check if text block is likely a footer based on content characteristics"""
        if not block.text:
            return False
        
        text = block.text.strip()
        
        # Skip empty or very short text
        if len(text) < 2:
            return False
        
        # Skip very long text (likely main content)
        if len(text) > 200:
            return False
        
        # Check for typical footer patterns
        footer_patterns = [
            # Page numbers
            r'^\d+$',
            # Page indicators
            r'^Page\s+\d+',
            r'^-\s*\d+\s*-$',
            # Date patterns
            r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$',
            r'^\d{4}-\d{2}-\d{2}$',
            # Copyright notices
            r'^©\s*\d{4}',
            r'^Copyright\s+\d{4}',
            # Confidential markings
            r'^(Confidential|Internal|Draft)',
            # File paths or document names
            r'^[A-Z]:\\',
            r'^/[a-zA-Z/]+$'
        ]
        
        import re
        for pattern in footer_patterns:
            if re.match(pattern, text):
                return True
        
        # Check if text is centered (typical for footers)
        if block.bbox and len(block.bbox) >= 4:
            block_center = (block.bbox[0] + block.bbox[2]) / 2
            page_center = page_width / 2
            # Allow some tolerance for centering
            if abs(block_center - page_center) < page_width * 0.1:
                return True
        
        # Check font size (footers often have smaller font)
        if block.font_size and block.font_size < 12:
            return True
        
        return False
    
    def _detect_columns(self, page_result: PageResult) -> PageResult:
        """Detect multi-column layout and reorder text blocks"""
        logger.warning(f"[DEBUG] Entered _detect_columns for page {page_result.page_number}, width={page_result.width}, text_blocks={len(page_result.text_blocks)}")
        if not page_result.text_blocks or page_result.width == 0:
            return page_result
        try:
            # 1. Use improved algorithm to analyze text block distribution and detect multi-column layout
            column_count = self._improve_column_detection(page_result)
            if column_count <= 1:
                # Single column layout, no need to reorder
                return page_result
            logger.warning(f"[DEBUG] Detected {column_count} columns layout")
            # 2. Assign text blocks to different columns
            columns = self._assign_blocks_to_columns(page_result, column_count)
            # 3. Sort text blocks within each column
            sorted_columns = self._sort_blocks_in_columns(columns)
            # 4. Reorder text blocks in reading order
            reordered_blocks = self._merge_columns_in_reading_order(sorted_columns, page_result.width)
            # 5. Update page result
            page_result.text_blocks = reordered_blocks
            # 6. Mark page as processed for multi-column layout
            page_result._column_processed = True
            return page_result
        except Exception as e:
            logger.warning(f"Multi-column detection failed, using original order: {e}")
            return page_result
    
    def _analyze_column_layout(self, page_result: PageResult) -> int:
        """Analyze page layout and detect number of columns"""
        if not page_result.text_blocks:
            return 1
        
        # Collect all x coordinates of text blocks
        x_positions = []
        for block in page_result.text_blocks:
            if block.bbox and len(block.bbox) >= 2:
                x_positions.append(block.bbox[0])  # x1 coordinate
        
        if not x_positions:
            return 1
        
        # Calculate page width
        page_width = page_result.width
        if page_width == 0:
            return 1
        
        # Use clustering method to detect number of columns
        column_count = self._detect_columns_by_clustering(x_positions, page_width)
        
        return column_count
    
    def _detect_columns_by_clustering(self, x_positions: List[float], page_width: float) -> int:
        """Detect number of columns using clustering method (优化版)"""
        if not x_positions:
            return 1
        unique_x = sorted(set(x_positions))
        if len(unique_x) < 2:
            return 1
        import numpy as np
        hist, bin_edges = np.histogram(unique_x, bins=min(20, len(unique_x)//2+1), range=(0, page_width))
        logger.warning(f"[DEBUG] x histogram: {hist}, bins: {bin_edges}")
        avg = np.mean(hist)
        gap_bins = [i for i, h in enumerate(hist) if h < avg*0.4]
        logger.warning(f"[DEBUG] Gap bins (possible column gaps): {gap_bins}")
        if len(gap_bins) > 0:
            for i in gap_bins:
                left = bin_edges[i]
                right = bin_edges[i+1]
                if left > page_width*0.25 and right < page_width*0.75:
                    logger.warning(f"[DEBUG] Detected large gap in middle: {left:.2f}-{right:.2f}, likely 2 columns")
                    return 2
        gaps = []
        for i in range(1, len(unique_x)):
            gap = unique_x[i] - unique_x[i-1]
            if gap > 20:
                gaps.append(gap)
        if not gaps:
            return 1
        avg_gap = sum(gaps) / len(gaps)
        large_gaps = [gap for gap in gaps if gap > avg_gap * 1.1 or gap > page_width * 0.2]
        if large_gaps:
            estimated_columns = self._estimate_column_count(page_width, large_gaps)
            return max(1, min(estimated_columns, 4))
        return 1
    
    def _estimate_column_count(self, page_width: float, large_gaps: List[float]) -> int:
        """Estimate number of columns based on page width and large gaps"""
        if not large_gaps:
            return 1
        
        # Calculate average column gap
        avg_column_gap = sum(large_gaps) / len(large_gaps)
        
        # Estimate number of columns based on page width and column gap
        # Assume each column has similar width, column gap is about 10-30% of page width
        if avg_column_gap > page_width * 0.15:
            # Large gap, possibly 2 columns
            return 2
        elif avg_column_gap > page_width * 0.08:
            # Medium gap, possibly 3 columns
            return 3
        else:
            # Small gap, possibly 4 or more columns
            return 4
    
    def _assign_blocks_to_columns(self, page_result: PageResult, column_count: int) -> List[List[TextBlock]]:
        """Assign text blocks to different columns"""
        columns = [[] for _ in range(column_count)]
        page_width = page_result.width
        
        # Calculate width and boundaries of each column
        column_width = page_width / column_count
        column_boundaries = []
        
        for i in range(column_count):
            left = i * column_width
            right = (i + 1) * column_width
            column_boundaries.append((left, right))
        
        # Assign text blocks to corresponding columns
        for block in page_result.text_blocks:
            if not block.bbox or len(block.bbox) < 2:
                # Blocks without position info go to the first column
                block.column_id = 0
                columns[0].append(block)
                continue
            
            block_center_x = (block.bbox[0] + block.bbox[2]) / 2
            
            # Find which column the block center is in
            assigned_column = 0
            for i, (left, right) in enumerate(column_boundaries):
                if left <= block_center_x < right:
                    assigned_column = i
                    break
            
            # Assign column_id to the block
            block.column_id = assigned_column
            columns[assigned_column].append(block)
        
        return columns
    
    def _sort_blocks_in_columns(self, columns: List[List[TextBlock]]) -> List[List[TextBlock]]:
        """Sort text blocks within each column (top to bottom, left to right)"""
        sorted_columns = []
        
        for column in columns:
            # Sort by y coordinate (top to bottom)
            sorted_column = sorted(column, key=lambda block: block.bbox[1] if block.bbox else 0)
            sorted_columns.append(sorted_column)
        
        return sorted_columns
    
    def _merge_columns_in_reading_order(self, sorted_columns: List[List[TextBlock]], page_width: float) -> List[TextBlock]:
        """Merge multi-column text blocks in reading order"""
        if not sorted_columns:
            return []
        
        # For patent documents and most academic papers, reading order is:
        # 1. Read all content in left column (top to bottom)
        # 2. Then read all content in right column (top to bottom)
        # This is different from newspaper-style reading (row by row)
        merged_blocks = []
        
        # Add all columns in order (left to right)
        for column in sorted_columns:
            merged_blocks.extend(column)
        
        return merged_blocks
    
    def _detect_reading_direction(self, text_blocks: List[TextBlock]) -> str:
        """Detect reading direction of the document"""
        if not text_blocks:
            return "ltr"  # left-to-right
        
        # Simple language detection (based on characters)
        chinese_chars = 0
        total_chars = 0
        
        for block in text_blocks:
            if block.text:
                for char in block.text:
                    total_chars += 1
                    # Detect Chinese characters
                    if '\u4e00' <= char <= '\u9fff':
                        chinese_chars += 1
        
        if total_chars > 0 and chinese_chars / total_chars > 0.3:
            return "ltr"  # Chinese, left-to-right
        else:
            return "ltr"  # Default left-to-right
    
    def _improve_column_detection(self, page_result: PageResult) -> int:
        """Improved column count detection method"""
        logger.warning(f"[DEBUG] Entered _improve_column_detection for page {page_result.page_number}")
        if not page_result.text_blocks:
            return 1
        logger.warning(f"[DEBUG] Page dimensions: {page_result.width} x {page_result.height}")
        logger.warning(f"[DEBUG] Number of text blocks: {len(page_result.text_blocks)}")
        # 输出所有文本块的 bbox（x1, x2）
        for i, block in enumerate(page_result.text_blocks):
            if block.bbox and len(block.bbox) >= 4:
                logger.warning(f"[DEBUG] Block {i+1}: x1={block.bbox[0]:.2f}, x2={block.bbox[2]:.2f}, text='{block.text[:30] if block.text else ''}'")
        # Method 1: Clustering analysis based on text block distribution
        column_count_1 = self._analyze_column_layout(page_result)
        logger.warning(f"[DEBUG] Method 1 (clustering): detected {column_count_1} columns")
        # Method 2: Heuristic detection based on page width
        column_count_2 = self._heuristic_column_detection(page_result)
        logger.warning(f"[DEBUG] Method 2 (heuristic): detected {column_count_2} columns")
        # Method 3: Density-based detection
        column_count_3 = self._density_based_column_detection(page_result)
        logger.warning(f"[DEBUG] Method 3 (density): detected {column_count_3} columns")
        # Combine results
        column_counts = [column_count_1, column_count_2, column_count_3]
        from collections import Counter
        counter = Counter(column_counts)
        most_common = counter.most_common(1)[0][0]
        logger.warning(f"[DEBUG] Column count detection: method1={column_count_1}, method2={column_count_2}, method3={column_count_3}, final={most_common}")
        return most_common
    
    def _heuristic_column_detection(self, page_result: PageResult) -> int:
        """Heuristic column count detection (优化版)"""
        if not page_result.text_blocks or page_result.width == 0:
            return 1
        block_widths = []
        x_centers = []
        for block in page_result.text_blocks:
            if block.bbox and len(block.bbox) >= 4:
                width = block.bbox[2] - block.bbox[0]
                block_widths.append(width)
                x_centers.append((block.bbox[0] + block.bbox[2]) / 2)
        if not block_widths:
            return 1
        avg_block_width = sum(block_widths) / len(block_widths)
        page_width = page_result.width
        import numpy as np
        if len(x_centers) > 10:
            from sklearn.cluster import KMeans
            X = np.array(x_centers).reshape(-1, 1)
            kmeans = KMeans(n_clusters=2, random_state=0).fit(X)
            centers = sorted([c[0] for c in kmeans.cluster_centers_])
            logger.warning(f"[DEBUG] KMeans x_centers: {centers}")
            if abs(centers[1] - centers[0]) > page_width * 0.3:
                logger.warning("[DEBUG] KMeans detected two column centers, likely 2 columns")
                return 2
        if avg_block_width < page_width * 0.45:
            estimated_columns = int(page_width / (avg_block_width * 1.1))
            return max(1, min(estimated_columns, 4))
        return 1
    
    def _density_based_column_detection(self, page_result: PageResult) -> int:
        """Density-based column count detection"""
        if not page_result.text_blocks or page_result.width == 0 or page_result.height == 0:
            return 1
        
        # Divide page into grid, calculate text density for each grid
        grid_size = 50  # grid size
        cols = int(page_result.width / grid_size) + 1
        rows = int(page_result.height / grid_size) + 1
        
        # Initialize density matrix
        density_matrix = [[0 for _ in range(cols)] for _ in range(rows)]
        
        # Calculate text density for each grid
        for block in page_result.text_blocks:
            if not block.bbox or len(block.bbox) < 4:
                continue
            
            # Calculate grids covered by block
            x1, y1, x2, y2 = block.bbox
            start_col = max(0, int(x1 / grid_size))
            end_col = min(cols - 1, int(x2 / grid_size))
            start_row = max(0, int(y1 / grid_size))
            end_row = min(rows - 1, int(y2 / grid_size))
            
            # Increase density for covered grids
            for row in range(start_row, end_row + 1):
                for col in range(start_col, end_col + 1):
                    density_matrix[row][col] += len(block.text) if block.text else 1
        
        # Analyze density distribution
        column_count = self._analyze_density_distribution(density_matrix, cols)
        
        return column_count
    
    def _analyze_density_distribution(self, density_matrix: List[List[int]], cols: int) -> int:
        """Analyze density distribution and detect number of columns"""
        if not density_matrix:
            return 1
        
        # Calculate average density for each column
        column_densities = []
        for col in range(cols):
            col_density = sum(density_matrix[row][col] for row in range(len(density_matrix)))
            column_densities.append(col_density)
        
        if not column_densities:
            return 1
        
        avg_density = sum(column_densities) / len(column_densities)
        threshold = avg_density * 0.3
        
        # Count number of high-density columns
        high_density_columns = sum(1 for density in column_densities if density > threshold)
        
        # Estimate number of columns based on number of high-density columns
        if high_density_columns <= 1:
            return 1
        elif high_density_columns <= 2:
            return 2
        elif high_density_columns <= 3:
            return 3
        else:
            return 4 