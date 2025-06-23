"""
Text Processor - Responsible for text cleaning and post-processing
"""

from typing import List
from loguru import logger

from ..config import ExtractionConfig
from ..models import ExtractionResult, TextBlock
from ..exceptions import SmartExtractorError


class TextProcessor:
    """Text Processor"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
    
    def post_process(self, result: ExtractionResult) -> ExtractionResult:
        """Post-process extraction result"""
        try:
            logger.info("Start text post-processing")
            
            # Clean text
            if self.config.enable_text_cleaning:
                result = self._clean_text(result)
            
            # Merge hyphenated words
            if self.config.merge_hyphenated_words:
                result = self._merge_hyphenated_words(result)
            
            # Remove headers and footers
            if self.config.remove_headers_footers:
                result = self._remove_headers_footers(result)
            
            # Fix encoding
            if self.config.fix_encoding:
                result = self._fix_encoding(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Text post-processing failed: {e}")
            raise SmartExtractorError(f"Text post-processing failed: {e}")
    
    def _clean_text(self, result: ExtractionResult) -> ExtractionResult:
        """Clean text"""
        # Check if any page has been processed for multi-column layout
        has_multi_column = any(
            hasattr(page, '_column_processed') and page._column_processed 
            for page in result.pages
        )
        
        if has_multi_column:
            # For multi-column pages, preserve the column structure
            # Only clean individual text blocks, not the merged text
            for page in result.pages:
                for block in page.text_blocks:
                    if block.text:
                        # Clean individual text blocks but preserve line breaks
                        block.text = ' '.join(block.text.split())
        else:
            # For single column pages, clean the merged text normally
            result.text = ' '.join(result.text.split())
            
            # Clean text blocks in each page
            for page in result.pages:
                for block in page.text_blocks:
                    if block.text:
                        block.text = ' '.join(block.text.split())
        
        return result
    
    def _merge_hyphenated_words(self, result: ExtractionResult) -> ExtractionResult:
        """Merge hyphenated words"""
        # TODO: Implement hyphenated word merging logic
        # Currently returns the original result
        return result
    
    def _remove_headers_footers(self, result: ExtractionResult) -> ExtractionResult:
        """Remove headers and footers"""
        # Filter out header and footer text blocks
        for page in result.pages:
            page.text_blocks = [
                block for block in page.text_blocks
                if block.block_type not in ['header', 'footer']
            ]
        
        # Only regenerate text if the page hasn't been processed for multi-column layout
        # This preserves the column grouping from _merge_results
        for page in result.pages:
            if not hasattr(page, '_column_processed') or not page._column_processed:
                # Single column page, regenerate text normally
                all_text = []
                for block in page.text_blocks:
                    if block.text:
                        all_text.append(block.text)
                # Update the page's text blocks to reflect the filtered content
                # but don't regenerate result.text to preserve column grouping
                pass
        
        return result
    
    def _fix_encoding(self, result: ExtractionResult) -> ExtractionResult:
        """Fix encoding issues"""
        # TODO: Implement encoding fix logic
        # Currently returns the original result
        return result 