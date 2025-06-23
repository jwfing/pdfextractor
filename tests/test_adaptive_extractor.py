import logging
from pathlib import Path

from smartextractor import AdaptivePDFExtractor

logger = logging.getLogger(__name__)

def test_extract_two_columns_pdf():
    extractor = AdaptivePDFExtractor()
    pdf_file = Path(__file__).parent.parent / "examples/patent22.pdf"
    context = extractor.extract_text(str(pdf_file))
    logger.info(f"{pdf_file} read result: {context}")
    print(f"{pdf_file} read result: {context}")
    assert len(context) > 0
    assert "BATTERY WITH MULTIPLE JELLY ROLLS of conductive tabs extend through seals in the pouch to" not in context
    assert "This application is a continuation of, and hereby claims In some embodiments" not in context

def test_single_column_pdf():
    extractor = AdaptivePDFExtractor()
    pdf_file = Path(__file__).parent.parent / "examples/Asset Purchase Agreement, dated as of April 22, 2021, by and _ Skyworks Solutions _ Business Contracts _ Justia.pdf"
    context = extractor.extract_text(str(pdf_file))
    logger.info(f"{pdf_file} read result: {context}")
    print(f"{pdf_file} read result: {context}")
    assert len(context) > 0