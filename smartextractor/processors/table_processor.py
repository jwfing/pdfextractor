"""
Table Processor - Responsible for table detection and extraction
"""

from typing import List
from loguru import logger

from ..config import ExtractionConfig
from ..models import TableResult, TableCell
from ..exceptions import TableExtractionError


class TableProcessor:
    """Table Processor"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
    
    def extract_tables(self, page_data, page_num: int) -> List[TableResult]:
        """Extract tables"""
        try:
            logger.info(f"Table extraction page {page_num}")
            
            tables = []
            
            # Process table data extracted from PDF
            for table_data in page_data.tables:
                table_result = self._process_table_data(table_data, page_num)
                if table_result:
                    tables.append(table_result)
            
            return tables
            
        except Exception as e:
            logger.error(f"Table extraction failed: {e}")
            raise TableExtractionError(f"Table extraction failed: {e}")
    
    def _process_table_data(self, table_data: dict, page_num: int) -> TableResult:
        """Process table data"""
        try:
            data = table_data.get('data', [])
            rows = table_data.get('rows', 0)
            cols = table_data.get('cols', 0)
            
            if not data or rows == 0 or cols == 0:
                return None
            
            # Create table cells
            cells = []
            for row_idx, row in enumerate(data):
                for col_idx, cell_text in enumerate(row):
                    if cell_text is not None:
                        cell = TableCell(
                            text=str(cell_text),
                            row=row_idx,
                            col=col_idx,
                            bbox=[0, 0, 0, 0],  # Use default value for now
                            is_header=row_idx == 0  # First row as header
                        )
                        cells.append(cell)
            
            return TableResult(
                cells=cells,
                rows=rows,
                cols=cols,
                bbox=[0, 0, 0, 0],  # Use default value for now
                page_number=page_num
            )
            
        except Exception as e:
            logger.warning(f"Failed to process table data: {e}")
            return None 