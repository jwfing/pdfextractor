import math
from pathlib import Path
from smartextractor.adaptive_pdfplumber import AdaptivePlumberExtractor
import pdfplumber

def detect_column_layout(file_path: str, target_num: int = 3) -> str:
    """
    这个方案不靠谱
    Detects if a PDF page has a one or two-column layout.

    Args:
        file_path: The path to the PDF file.
        target_num: The page number to analyze (0-indexed).

    Returns:
        A string: "one-column", "two-column", or "unknown".
    """
    try:
        with pdfplumber.open(file_path) as pdf:
            num_pages = len(pdf.pages)
            page_number = target_num
            if num_pages <= 1:
                page_number = 0
            elif num_pages <= 4:
                page_number = math.ceil(num_pages / 2)
            page = pdf.pages[page_number]

            # Get the horizontal center of the page
            center_x = page.width / 2

            # Define a small vertical strip (gutter) around the center
            # We'll check if this area is mostly empty.
            # A 5% width for the gutter is a reasonable starting point.
            gutter_width = page.width * 0.05
            gutter_box = (
                center_x - (gutter_width / 2),
                0,
                center_x + (gutter_width / 2),
                page.height
            )
            print(f"gutter_box: {gutter_box}")

            # Find words that are completely outside the central gutter
            words_outside_gutter = [
                word for word in page.extract_words()
                if word['x0'] > gutter_box[2] or word['x1'] < gutter_box[0]
            ]
            print(f"words_outside_gutter: {len(words_outside_gutter)}")
            words_inside_gutter = [
                word for word in page.extract_words()
                if word['x0'] > gutter_box[0] and word['x1'] < gutter_box[2]
            ]
            print(f"words_inside_gutter: {len(words_inside_gutter)}")

            if not words_outside_gutter:
                # This could be an empty page or a page with only a centered title
                return "one-column"

            if not words_inside_gutter:
                return "two-column"

            # Check for the presence of text on both left and right sides of the page
            left_text_exists = any(word['x0'] < center_x for word in words_outside_gutter)
            right_text_exists = any(word['x1'] > center_x for word in words_outside_gutter)
            print(f"left_text_exists: {left_text_exists}")
            print(f"right_text_exists: {right_text_exists}")

            if left_text_exists and right_text_exists:
                # If text exists on both sides, it's very likely a two-column layout
                return "two-column"
            else:
                return "one-column"

    except Exception as e:
        print(f"An error occurred: {e}")
        return "unknown"

def test_layout_detect_for_all_files():
    user_files_dir = Path(__file__).parent.parent / "examples"
    # 查找目录中所有的 PDF 文件
    pdf_files = list(user_files_dir.glob("*.pdf"))
    assert len(pdf_files) > 0, f"No PDF files found in {user_files_dir}"

    for pdf_path in pdf_files:
        layout_type = detect_column_layout(str(pdf_path))
        print(f"使用自动列检测处理文件: {str(pdf_path)}, 布局类型: {layout_type} ---")


def test_extract_all_files():
    extractor = AdaptivePlumberExtractor()
    user_files_dir = Path(__file__).parent.parent / "examples"
    # 查找目录中所有的 PDF 文件
    pdf_files = list(user_files_dir.glob("*.pdf"))
    assert len(pdf_files) > 0, f"No PDF files found in {user_files_dir}"

    for pdf_path in pdf_files:
        try:
            print(f"--- 正在使用自动列检测处理文件: {str(pdf_path)} ---")
            extracted_text = extractor.extract_text(str(pdf_path))
        except FileNotFoundError:
            print(f"错误: 文件未找到 {pdf_path}")
        except ImportError:
            print("错误: 请确保已安装 scikit-learn 和 numpy (`pip install scikit-learn numpy`)")
        except Exception as e:
            print(f"处理过程中发生错误: {e}")