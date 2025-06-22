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
        """Detect headers and footers"""
        page_height = page_result.height
        
        for block in page_result.text_blocks:
            if block.bbox:
                y_pos = block.bbox[1]  # y coordinate
                
                # Detect header (top of page)
                if y_pos < page_height * 0.1:
                    block.block_type = "header"
                
                # Detect footer (bottom of page)
                elif y_pos > page_height * 0.9:
                    block.block_type = "footer"
        
        return page_result
    
    def _detect_columns(self, page_result: PageResult) -> PageResult:
        """Detect multi-column layout and reorder text blocks"""
        if not page_result.text_blocks or page_result.width == 0:
            return page_result
        
        try:
            # 1. Use improved algorithm to analyze text block distribution and detect multi-column layout
            column_count = self._improve_column_detection(page_result)
            
            if column_count <= 1:
                # Single column layout, no need to reorder
                return page_result
            
            logger.info(f"Detected {column_count} columns layout")
            
            # 2. Assign text blocks to different columns
            columns = self._assign_blocks_to_columns(page_result, column_count)
            
            # 3. Sort text blocks within each column
            sorted_columns = self._sort_blocks_in_columns(columns)
            
            # 4. Reorder text blocks in reading order
            reordered_blocks = self._merge_columns_in_reading_order(sorted_columns, page_result.width)
            
            # 5. Update page result
            page_result.text_blocks = reordered_blocks
            
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
        """Detect number of columns using clustering method"""
        if not x_positions:
            return 1
        
        # Get unique x coordinates and sort them
        unique_x = sorted(set(x_positions))
        
        if len(unique_x) < 2:
            return 1
        
        # Calculate differences between adjacent unique x coordinates
        gaps = []
        for i in range(1, len(unique_x)):
            gap = unique_x[i] - unique_x[i-1]
            if gap > 20:  # Ignore small gaps
                gaps.append(gap)
        
        if not gaps:
            return 1
        
        # Calculate average gap
        avg_gap = sum(gaps) / len(gaps)
        
        # If there are large gaps (possibly column gaps), it may be a multi-column layout
        # Use both relative and absolute thresholds
        large_gaps = []
        for gap in gaps:
            if gap > avg_gap * 1.1 or gap > page_width * 0.3:  # Relative or absolute threshold
                large_gaps.append(gap)
        
        if large_gaps:
            # Estimate number of columns based on number of large gaps and page width
            estimated_columns = self._estimate_column_count(page_width, large_gaps)
            return max(1, min(estimated_columns, 4))  # Limit to 1-4 columns
        
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
                columns[0].append(block)
                continue
            
            block_center_x = (block.bbox[0] + block.bbox[2]) / 2
            
            # Find which column the block center is in
            assigned_column = 0
            for i, (left, right) in enumerate(column_boundaries):
                if left <= block_center_x < right:
                    assigned_column = i
                    break
            
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
        
        # For most documents, reading order is left-to-right, top-to-bottom
        merged_blocks = self._merge_columns_by_row_alignment(sorted_columns)
        
        return merged_blocks
    
    def _merge_columns_by_row_alignment(self, sorted_columns: List[List[TextBlock]]) -> List[TextBlock]:
        """Merge multi-column blocks based on row alignment"""
        if not sorted_columns:
            return []
        
        # Collect all y coordinates for row alignment
        all_blocks = []
        for column in sorted_columns:
            all_blocks.extend(column)
        
        if not all_blocks:
            return []
        
        # Sort all blocks by y coordinate
        all_blocks.sort(key=lambda block: block.bbox[1] if block.bbox else 0)
        
        # Group blocks by rows
        row_groups = self._group_blocks_by_rows(all_blocks)
        
        # Sort blocks within each row by x coordinate (left to right)
        merged_blocks = []
        for row_group in row_groups:
            row_group.sort(key=lambda block: block.bbox[0] if block.bbox else 0)
            merged_blocks.extend(row_group)
        
        return merged_blocks
    
    def _group_blocks_by_rows(self, blocks: List[TextBlock], tolerance: float = 10.0) -> List[List[TextBlock]]:
        """Group text blocks by rows"""
        if not blocks:
            return []
        
        # Separate blocks with and without bbox
        blocks_with_bbox = []
        blocks_without_bbox = []
        
        for block in blocks:
            if block.bbox:
                blocks_with_bbox.append(block)
            else:
                blocks_without_bbox.append(block)
        
        # Sort by y coordinate
        sorted_blocks = sorted(blocks_with_bbox, key=lambda block: block.bbox[1] if block.bbox else 0)
        
        row_groups = []
        current_row = []
        current_y = None
        
        for block in sorted_blocks:
            block_y = block.bbox[1]
            
            if current_y is None:
                # First block
                current_y = block_y
                current_row = [block]
            elif abs(block_y - current_y) <= tolerance:
                # Same row
                current_row.append(block)
            else:
                # New row
                if current_row:
                    row_groups.append(current_row)
                current_y = block_y
                current_row = [block]
        
        # Add last row
        if current_row:
            row_groups.append(current_row)
        
        # Add blocks without bbox to the first row or create a new row
        if blocks_without_bbox:
            if row_groups:
                row_groups[0].extend(blocks_without_bbox)
            else:
                row_groups.append(blocks_without_bbox)
        
        return row_groups
    
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
        if not page_result.text_blocks:
            return 1
        
        # Method 1: Clustering analysis based on text block distribution
        column_count_1 = self._analyze_column_layout(page_result)
        
        # Method 2: Heuristic detection based on page width
        column_count_2 = self._heuristic_column_detection(page_result)
        
        # Method 3: Density-based detection
        column_count_3 = self._density_based_column_detection(page_result)
        
        # Combine results
        column_counts = [column_count_1, column_count_2, column_count_3]
        from collections import Counter
        counter = Counter(column_counts)
        most_common = counter.most_common(1)[0][0]
        
        logger.info(f"Column count detection: method1={column_count_1}, method2={column_count_2}, method3={column_count_3}, final={most_common}")
        
        return most_common
    
    def _heuristic_column_detection(self, page_result: PageResult) -> int:
        """Heuristic column count detection"""
        if not page_result.text_blocks or page_result.width == 0:
            return 1
        
        # Calculate average width of text blocks
        block_widths = []
        for block in page_result.text_blocks:
            if block.bbox and len(block.bbox) >= 4:
                width = block.bbox[2] - block.bbox[0]
                block_widths.append(width)
        
        if not block_widths:
            return 1
        
        avg_block_width = sum(block_widths) / len(block_widths)
        page_width = page_result.width
        
        # If average block width is less than half of page width, may be multi-column
        if avg_block_width < page_width * 0.4:
            # Use a smaller coefficient for better two-column detection
            estimated_columns = int(page_width / (avg_block_width * 1.2))
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