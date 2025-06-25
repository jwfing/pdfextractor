import logging
from pathlib import Path

from smartextractor import AdaptiveFitzExtractor

logger = logging.getLogger(__name__)

def test_extract_two_columns_pdf():
    extractor = AdaptiveFitzExtractor()
    pdf_file = Path(__file__).parent.parent / "examples/patent22.pdf"
    context = extractor.extract_text(str(pdf_file))
    logger.info(f"{pdf_file} read result: {len(context)}")
    assert len(context) > 0
    assert "BATTERY WITH MULTIPLE JELLY ROLLS of conductive tabs extend through seals in the pouch to" not in context
    assert "This application is a continuation of, and hereby claims In some embodiments" not in context

def test_single_column_pdf():
    extractor = AdaptiveFitzExtractor()
    pdf_file = Path(__file__).parent.parent / "examples/Asset Purchase Agreement, dated as of April 22, 2021, by and _ Skyworks Solutions _ Business Contracts _ Justia.pdf"
    context = extractor.extract_text(str(pdf_file))
    logger.info(f"{pdf_file} read result: {len(context)}")
    assert len(context) > 0

def test_read_all_pdf_files():
    extractor = AdaptiveFitzExtractor()
    user_files_dir = Path(__file__).parent.parent / "examples"
    # 查找目录中所有的 PDF 文件
    pdf_files = list(user_files_dir.glob("*.pdf"))
    assert len(pdf_files) > 0, f"No PDF files found in {user_files_dir}"

    logger.info(f"\nFound {len(pdf_files)} PDF files to test.")

    for pdf_file in pdf_files:
        print(f"try to read {pdf_file}")
        context = extractor.extract_text(str(pdf_file))
        logger.info(f"\t{pdf_file}: {len(context)}")
        assert len(context) >= 0