"""
Command Line Interface - Provides CLI tools
"""

import os
import sys
from pathlib import Path
from typing import Optional

import click
from loguru import logger

from .core import SmartExtractor
from .config import ExtractionConfig
from .exceptions import SmartExtractorError


@click.group()
@click.version_option(version="0.1.0")
def main():
    """SmartExtractor - Intelligent PDF Text Extraction Tool"""
    pass


@main.command()
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('-o', '--output', type=click.Path(), help='Output file path')
@click.option('--format', 'output_format', 
              type=click.Choice(['text', 'json', 'structured']), 
              default='text', help='Output format')
@click.option('--language', default='en', help='Document language')
@click.option('--enable-ocr/--disable-ocr', default=True, help='Enable/Disable OCR')
@click.option('--enable-layout/--disable-layout', default=True, help='Enable/Disable layout detection')
@click.option('--enable-tables/--disable-tables', default=True, help='Enable/Disable table extraction')
@click.option('--confidence', type=float, default=0.8, help='Confidence threshold')
@click.option('--workers', type=int, default=4, help='Number of parallel workers')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def extract(pdf_path, output, output_format, language, enable_ocr, 
           enable_layout, enable_tables, confidence, workers, verbose):
    """Extract text content from PDF"""
    
    # Set log level
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")
    
    try:
        # Create config
        config = ExtractionConfig(
            enable_ocr=enable_ocr,
            enable_layout_detection=enable_layout,
            enable_table_extraction=enable_tables,
            language=language,
            confidence_threshold=confidence,
            max_workers=workers,
            output_format=output_format
        )
        
        # Create extractor
        extractor = SmartExtractor(config)
        
        # Extract content
        logger.info(f"Start extracting PDF: {pdf_path}")
        result = extractor.extract(pdf_path)
        
        # Output result
        if output:
            _save_result(result, output, output_format)
            logger.info(f"Result saved to: {output}")
        else:
            _print_result(result, output_format)
            
    except SmartExtractorError as e:
        logger.error(f"Extraction failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unknown error: {e}")
        sys.exit(1)


@main.command()
@click.argument('pdf_path', type=click.Path(exists=True))
def info(pdf_path):
    """Show PDF file information"""
    try:
        config = ExtractionConfig()
        extractor = SmartExtractor(config)
        
        # Get processing stats
        stats = extractor.get_processing_stats()
        
        click.echo(f"PDF file: {pdf_path}")
        click.echo(f"File size: {os.path.getsize(pdf_path)} bytes")
        click.echo(f"OCR enabled: {'Yes' if stats['ocr_enabled'] else 'No'}")
        click.echo(f"Layout detection: {'Yes' if stats['layout_detection_enabled'] else 'No'}")
        click.echo(f"Table extraction: {'Yes' if stats['table_extraction_enabled'] else 'No'}")
        click.echo(f"Supported languages: {', '.join(stats['supported_languages'])}")
        
    except Exception as e:
        logger.error(f"Failed to get info: {e}")
        sys.exit(1)


@main.command()
def languages():
    """Show supported languages"""
    try:
        config = ExtractionConfig()
        extractor = SmartExtractor(config)
        
        languages = extractor.get_supported_languages()
        
        click.echo("Supported languages:")
        for lang in languages:
            click.echo(f"  - {lang}")
            
    except Exception as e:
        logger.error(f"Failed to get language list: {e}")
        sys.exit(1)


def _save_result(result, output_path: str, output_format: str):
    """Save result to file"""
    if output_format == 'text':
        result.save_text(output_path)
    elif output_format == 'json':
        result.save_json(output_path)
    elif output_format == 'structured':
        # Save structured data
        result.save_json(output_path)


def _print_result(result, output_format: str):
    """Print result to console"""
    if output_format == 'text':
        click.echo(result.text)
    elif output_format == 'json':
        click.echo(result.to_json())
    elif output_format == 'structured':
        # Print structured info
        click.echo(f"Text length: {len(result.text)} characters")
        click.echo(f"Number of pages: {len(result.pages)}")
        click.echo(f"Number of tables: {len(result.tables)}")
        click.echo(f"Number of images: {len(result.images)}")
        click.echo(f"Processing time: {result.processing_time:.2f} seconds")
        click.echo("\nText content:")
        click.echo(result.text)


if __name__ == '__main__':
    main() 