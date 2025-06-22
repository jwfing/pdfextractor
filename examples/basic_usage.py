#!/usr/bin/env python3
"""
SmartExtractor Basic Usage Example
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from smartextractor import SmartExtractor, ExtractionConfig


def basic_extraction_example():
    """Basic extraction example"""
    print("=== SmartExtractor Basic Usage Example ===\n")
    
    # Create extractor instance
    extractor = SmartExtractor()
    
    # Show configuration info
    print("Current configuration:")
    stats = extractor.get_processing_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    # Show supported languages
    print("Supported languages:")
    languages = extractor.get_supported_languages()
    for lang in languages:
        print(f"  - {lang}")
    print()
    
    # Note: You need an actual PDF file to demonstrate
    print("Note: To test PDF extraction, please prepare a PDF file.")
    print("Then use the following code:")
    print()
    print("```python")
    print("# Extract text")
    print("text = extractor.extract_text('your_document.pdf')")
    print("print(text)")
    print()
    print("# Extract full result")
    print("result = extractor.extract('your_document.pdf')")
    print("print(f'Text length: {len(result.text)}')")
    print("print(f'Number of pages: {len(result.pages)}')")
    print("print(f'Number of tables: {len(result.tables)}')")
    print("```")


def advanced_config_example():
    """Advanced configuration example"""
    print("=== Advanced Configuration Example ===\n")
    
    # Create custom config
    config = ExtractionConfig(
        enable_ocr=True,
        enable_layout_detection=True,
        enable_table_extraction=True,
        language="zh-CN",
        confidence_threshold=0.8,
        max_workers=2,
        output_format="structured"
    )
    
    # Create extractor with custom config
    extractor = SmartExtractor(config)
    
    print("Custom configuration:")
    print(f"  OCR enabled: {config.enable_ocr}")
    print(f"  Layout detection: {config.enable_layout_detection}")
    print(f"  Table extraction: {config.enable_table_extraction}")
    print(f"  Language: {config.language}")
    print(f"  Confidence threshold: {config.confidence_threshold}")
    print(f"  Number of workers: {config.max_workers}")
    print(f"  Output format: {config.output_format}")


def command_line_example():
    """Command line usage example"""
    print("=== Command Line Usage Example ===\n")
    
    print("Basic extraction:")
    print("  smartextractor extract document.pdf")
    print()
    
    print("Specify output file:")
    print("  smartextractor extract document.pdf -o output.txt")
    print()
    
    print("JSON output:")
    print("  smartextractor extract document.pdf --format json -o output.json")
    print()
    
    print("Custom configuration:")
    print("  smartextractor extract document.pdf --language en --confidence 0.9")
    print()
    
    print("Show file info:")
    print("  smartextractor info document.pdf")
    print()
    
    print("Show supported languages:")
    print("  smartextractor languages")


if __name__ == "__main__":
    basic_extraction_example()
    print("\n" + "="*50 + "\n")
    advanced_config_example()
    print("\n" + "="*50 + "\n")
    command_line_example() 