#!/usr/bin/env python3
"""
Column Layout Detection Demo
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from smartextractor import SmartExtractor, ExtractionConfig
from smartextractor.models import PageResult, TextBlock
from smartextractor.processors.layout_processor import LayoutProcessor


def create_test_page_result():
    """Create test page result"""
    # Simulate a two-column layout page
    page_result = PageResult(
        page_number=1,
        width=800,
        height=600,
        text_blocks=[
            # Left column content
            TextBlock(text="Left column paragraph 1: This is the first paragraph in the left column, containing some sample text.", 
                     bbox=[50, 50, 350, 80], font_size=12),
            TextBlock(text="Left column paragraph 2: This is the second paragraph in the left column, continuing to show the effect of multi-column layout.", 
                     bbox=[50, 100, 350, 130], font_size=12),
            TextBlock(text="Left column paragraph 3: The last paragraph in the left column, used to demonstrate text reordering.", 
                     bbox=[50, 150, 350, 180], font_size=12),
            
            # Right column content
            TextBlock(text="Right column paragraph 1: This is the first paragraph in the right column, arranged parallel to the left column.", 
                     bbox=[450, 50, 750, 80], font_size=12),
            TextBlock(text="Right column paragraph 2: The second paragraph in the right column, showing the reading order of multi-column layout.", 
                     bbox=[450, 100, 750, 130], font_size=12),
            TextBlock(text="Right column paragraph 3: The last paragraph in the right column, completing the demo page.", 
                     bbox=[450, 150, 750, 180], font_size=12),
        ]
    )
    
    return page_result


def demo_column_detection():
    """Demonstrate multi-column layout detection"""
    print("=== Column Layout Detection Demo ===\n")
    
    # Create test page
    page_result = create_test_page_result()
    
    print("Original text block order (simulated raw PDF extraction order):")
    for i, block in enumerate(page_result.text_blocks):
        print(f"  {i+1}. {block.text}")
    print()
    
    # Create layout processor
    config = ExtractionConfig(enable_layout_detection=True, detect_columns=True)
    processor = LayoutProcessor(config)
    
    # Process page
    print("Detecting column layout...")
    processed_result = processor.process(page_result, None)
    
    print("\nText block order after processing (reordered by reading order):")
    for i, block in enumerate(processed_result.text_blocks):
        print(f"  {i+1}. {block.text}")
    print()
    
    # Show detected column count
    column_count = processor._improve_column_detection(page_result)
    print(f"Detected column count: {column_count}")
    
    # Show text blocks in each column
    if column_count > 1:
        columns = processor._assign_blocks_to_columns(page_result, column_count)
        for i, column in enumerate(columns):
            print(f"\nText blocks in column {i+1}:")
            for j, block in enumerate(column):
                print(f"  {j+1}. {block.text}")


def demo_different_layouts():
    """Demonstrate detection of different layouts"""
    print("\n=== Different Layouts Detection Demo ===\n")
    
    config = ExtractionConfig(enable_layout_detection=True, detect_columns=True)
    processor = LayoutProcessor(config)
    
    # Test single column layout
    single_column_page = PageResult(
        page_number=1,
        width=800,
        height=600,
        text_blocks=[
            TextBlock(text="Single column paragraph 1", bbox=[50, 50, 750, 80]),
            TextBlock(text="Single column paragraph 2", bbox=[50, 100, 750, 130]),
            TextBlock(text="Single column paragraph 3", bbox=[50, 150, 750, 180]),
        ]
    )
    
    column_count = processor._improve_column_detection(single_column_page)
    print(f"Single column layout detection result: {column_count} column(s)")
    
    # Test three column layout
    three_column_page = PageResult(
        page_number=1,
        width=900,
        height=600,
        text_blocks=[
            TextBlock(text="Left column", bbox=[50, 50, 250, 80]),
            TextBlock(text="Center column", bbox=[350, 50, 550, 80]),
            TextBlock(text="Right column", bbox=[650, 50, 850, 80]),
        ]
    )
    
    column_count = processor._improve_column_detection(three_column_page)
    print(f"Three column layout detection result: {column_count} column(s)")


def demo_row_grouping():
    """Demonstrate row grouping function"""
    print("\n=== Row Grouping Demo ===\n")
    
    config = ExtractionConfig()
    processor = LayoutProcessor(config)
    
    # Create test text blocks
    blocks = [
        TextBlock(text="Row 1 Left", bbox=[50, 100, 200, 130]),
        TextBlock(text="Row 1 Right", bbox=[250, 100, 400, 130]),
        TextBlock(text="Row 2 Left", bbox=[50, 150, 200, 180]),
        TextBlock(text="Row 2 Right", bbox=[250, 150, 400, 180]),
        TextBlock(text="Row 3 Left", bbox=[50, 200, 200, 230]),
        TextBlock(text="Row 3 Right", bbox=[250, 200, 400, 230]),
    ]
    
    # Perform row grouping
    row_groups = processor._group_blocks_by_rows(blocks)
    
    print(f"Detected {len(row_groups)} row(s):")
    for i, row in enumerate(row_groups):
        print(f"  Row {i+1}: {[block.text for block in row]}")


if __name__ == "__main__":
    demo_column_detection()
    demo_different_layouts()
    demo_row_grouping()
    
    print("\n=== Demo Complete ===")
    print("\nInstructions:")
    print("1. This demo shows multi-column layout detection and text reordering.")
    print("2. For two-column PDFs, text will be reordered from left to right, top to bottom.")
    print("3. This ensures the extracted text matches the normal reading order.")
    print("4. In actual use, just enable layout detection to automatically handle multi-column layouts.") 