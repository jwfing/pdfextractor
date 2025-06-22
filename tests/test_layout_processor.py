"""
Layout Processor Tests
"""

import pytest
from smartextractor.processors.layout_processor import LayoutProcessor
from smartextractor.config import ExtractionConfig
from smartextractor.models import PageResult, TextBlock


class TestLayoutProcessor:
    """Layout Processor Test Class"""
    
    def setup_method(self):
        """Set up test environment"""
        self.config = ExtractionConfig()
        self.processor = LayoutProcessor(self.config)
    
    def test_detect_headers(self):
        """Test header detection"""
        # Create test page
        page_result = PageResult(
            page_number=1,
            width=800,
            height=600,
            text_blocks=[
                TextBlock(text="Big Title", bbox=[0, 0, 200, 50], font_size=18),
                TextBlock(text="Body Content", bbox=[0, 60, 400, 80], font_size=12),
                TextBlock(text="Subtitle", bbox=[0, 100, 150, 120], font_size=16),
            ]
        )
        
        # Process page
        result = self.processor._detect_headers(page_result)
        
        # Check results
        assert result.text_blocks[0].block_type == "title"  # Big Title
        assert result.text_blocks[1].block_type == "text"   # Body
        assert result.text_blocks[2].block_type == "title"  # Subtitle
    
    def test_detect_headers_footers(self):
        """Test header/footer detection"""
        page_result = PageResult(
            page_number=1,
            width=800,
            height=600,
            text_blocks=[
                TextBlock(text="Header", bbox=[0, 0, 100, 30]),      # Top
                TextBlock(text="Body", bbox=[0, 100, 400, 200]),   # Middle
                TextBlock(text="Footer", bbox=[0, 570, 100, 600]),   # Bottom
            ]
        )
        
        result = self.processor._detect_headers_footers(page_result)
        
        assert result.text_blocks[0].block_type == "header"
        assert result.text_blocks[1].block_type == "text"
        assert result.text_blocks[2].block_type == "footer"
    
    def test_single_column_layout(self):
        """Test single column layout"""
        page_result = PageResult(
            page_number=1,
            width=800,
            height=600,
            text_blocks=[
                TextBlock(text="Paragraph 1", bbox=[50, 50, 750, 80]),
                TextBlock(text="Paragraph 2", bbox=[50, 100, 750, 130]),
                TextBlock(text="Paragraph 3", bbox=[50, 150, 750, 180]),
            ]
        )
        
        result = self.processor._detect_columns(page_result)
        
        # Single column layout should remain unchanged
        assert len(result.text_blocks) == 3
        assert result.text_blocks[0].text == "Paragraph 1"
        assert result.text_blocks[1].text == "Paragraph 2"
        assert result.text_blocks[2].text == "Paragraph 3"
    
    def test_two_column_layout(self):
        """Test two column layout"""
        page_result = PageResult(
            page_number=1,
            width=800,
            height=600,
            text_blocks=[
                # Left column
                TextBlock(text="Left Column 1", bbox=[50, 50, 350, 80]),
                TextBlock(text="Left Column 2", bbox=[50, 100, 350, 130]),
                # Right column
                TextBlock(text="Right Column 1", bbox=[450, 50, 750, 80]),
                TextBlock(text="Right Column 2", bbox=[450, 100, 750, 130]),
            ]
        )
        
        result = self.processor._detect_columns(page_result)
        
        # Should detect two columns and reorder
        assert len(result.text_blocks) == 4
        
        # Check reading order (left to right, top to bottom)
        # Row 1: Left Column 1, Right Column 1
        # Row 2: Left Column 2, Right Column 2
        expected_order = [
            "Left Column 1", "Right Column 1", 
            "Left Column 2", "Right Column 2"
        ]
        
        actual_order = [block.text for block in result.text_blocks]
        assert actual_order == expected_order
    
    def test_three_column_layout(self):
        """Test three column layout"""
        page_result = PageResult(
            page_number=1,
            width=900,
            height=600,
            text_blocks=[
                # Left column
                TextBlock(text="Left", bbox=[50, 50, 250, 80]),
                # Center column
                TextBlock(text="Center", bbox=[350, 50, 550, 80]),
                # Right column
                TextBlock(text="Right", bbox=[650, 50, 850, 80]),
            ]
        )
        
        result = self.processor._detect_columns(page_result)
        
        # Should detect three columns
        assert len(result.text_blocks) == 3
        
        # Check left-to-right order
        expected_order = ["Left", "Center", "Right"]
        actual_order = [block.text for block in result.text_blocks]
        assert actual_order == expected_order
    
    def test_group_blocks_by_rows(self):
        """Test text block row grouping"""
        blocks = [
            TextBlock(text="Row1-Left", bbox=[50, 100, 200, 130]),
            TextBlock(text="Row1-Right", bbox=[250, 100, 400, 130]),
            TextBlock(text="Row2-Left", bbox=[50, 150, 200, 180]),
            TextBlock(text="Row2-Right", bbox=[250, 150, 400, 180]),
        ]
        
        row_groups = self.processor._group_blocks_by_rows(blocks)
        
        assert len(row_groups) == 2
        assert len(row_groups[0]) == 2  # First row
        assert len(row_groups[1]) == 2  # Second row
        
        # Check blocks in first row
        first_row_texts = [block.text for block in row_groups[0]]
        assert "Row1-Left" in first_row_texts
        assert "Row1-Right" in first_row_texts
    
    def test_heuristic_column_detection(self):
        """Test heuristic column count detection"""
        # Test narrow text blocks (likely multi-column)
        page_result = PageResult(
            page_number=1,
            width=800,
            height=600,
            text_blocks=[
                TextBlock(text="Narrow Text", bbox=[50, 50, 200, 80]),  # width 150
                TextBlock(text="Narrow Text", bbox=[250, 50, 400, 80]), # width 150
            ]
        )
        
        column_count = self.processor._heuristic_column_detection(page_result)
        assert column_count >= 2  # Should detect multi-column
        
        # Test wide text block (likely single column)
        page_result = PageResult(
            page_number=1,
            width=800,
            height=600,
            text_blocks=[
                TextBlock(text="Wide Text", bbox=[50, 50, 750, 80]),  # width 700
            ]
        )
        
        column_count = self.processor._heuristic_column_detection(page_result)
        assert column_count == 1  # Should detect single column
    
    def test_density_based_column_detection(self):
        """Test density-based column count detection"""
        page_result = PageResult(
            page_number=1,
            width=800,
            height=600,
            text_blocks=[
                # Left column dense text
                TextBlock(text="Left Text 1", bbox=[50, 50, 350, 80]),
                TextBlock(text="Left Text 2", bbox=[50, 100, 350, 130]),
                # Right column dense text
                TextBlock(text="Right Text 1", bbox=[450, 50, 750, 80]),
                TextBlock(text="Right Text 2", bbox=[450, 100, 750, 130]),
            ]
        )
        
        column_count = self.processor._density_based_column_detection(page_result)
        assert column_count >= 2  # Should detect multi-column
    
    def test_improve_column_detection(self):
        """Test improved column count detection"""
        page_result = PageResult(
            page_number=1,
            width=800,
            height=600,
            text_blocks=[
                # Two-column layout
                TextBlock(text="Left", bbox=[50, 50, 350, 80]),
                TextBlock(text="Right", bbox=[450, 50, 750, 80]),
            ]
        )
        
        column_count = self.processor._improve_column_detection(page_result)
        assert column_count >= 1 and column_count <= 4  # Should be in reasonable range
    
    def test_empty_page(self):
        """Test empty page"""
        page_result = PageResult(
            page_number=1,
            width=800,
            height=600,
            text_blocks=[]
        )
        
        result = self.processor._detect_columns(page_result)
        assert len(result.text_blocks) == 0
    
    def test_blocks_without_bbox(self):
        """Test text blocks without bbox"""
        page_result = PageResult(
            page_number=1,
            width=800,
            height=600,
            text_blocks=[
                TextBlock(text="No position info", bbox=None),
                TextBlock(text="Has position info", bbox=[50, 50, 200, 80]),
            ]
        )
        
        result = self.processor._detect_columns(page_result)
        assert len(result.text_blocks) == 2  # Should keep all blocks 