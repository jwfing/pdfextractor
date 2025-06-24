from pathlib import Path

from smartextractor.adaptive_pdfplumber import AdaptivePlumberExtractor

def test_extract_all_files():
    extractor = AdaptivePlumberExtractor()
    user_files_dir = Path(__file__).parent.parent / "examples"
    # 查找目录中所有的 PDF 文件
    pdf_files = list(user_files_dir.glob("*.pdf"))
    assert len(pdf_files) > 0, f"No PDF files found in {user_files_dir}"

    for pdf_path in pdf_files:
        try:
            print(f"--- 正在使用自动列检测处理文件: {pdf_path} ---")
            extracted_text = extractor.extract_text(str(pdf_path))
        except FileNotFoundError:
            print(f"错误: 文件未找到 {pdf_path}")
        except ImportError:
            print("错误: 请确保已安装 scikit-learn 和 numpy (`pip install scikit-learn numpy`)")
        except Exception as e:
            print(f"处理过程中发生错误: {e}")