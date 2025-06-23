import pdfplumber
import numpy as np
from sklearn.cluster import KMeans
import warnings


def extract_text_from_multi_column_auto(page: pdfplumber.page.Page, n_columns: int = 2) -> str:
    """
    使用 K-Means 聚类算法自动检测并提取多栏页面的文本。

    Args:
        page: 一个 pdfplumber.page.Page 对象。
        n_columns: 希望检测的列数，默认为 2。

    Returns:
        提取并正确排序后的文本。
    """
    # 1. 获取页面上的所有单词。使用单词比文本块更精细，效果更好。
    # x_tolerance=3 允许多个字符被合并成一个单词
    words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False)

    if not words:
        # 如果页面上没有单词，尝试用默认方法提取
        return page.extract_text()

    # 2. 计算每个单词的水平中心点
    x_centers = np.array([(word['x0'] + word['x1']) / 2 for word in words]).reshape(-1, 1)

    # 3. 使用 K-Means 算法寻找列的中心
    # 抑制 scikit-learn 新版本中关于 n_init 的警告
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        kmeans = KMeans(n_clusters=n_columns, random_state=42, n_init=10).fit(x_centers)

    # 4. 获取并排序聚类中心（即每列的中心线 x 坐标）
    column_centers = sorted(kmeans.cluster_centers_.flatten())

    # 5. 合理性检查：如果列中心靠得太近，可能实际上是单栏布局
    # 我们定义一个最小间距，比如页面宽度的 10%
    min_separation = page.width * 0.1
    is_multi_column = True
    for i in range(len(column_centers) - 1):
        if (column_centers[i + 1] - column_centers[i]) < min_separation:
            is_multi_column = False
            break

    if not is_multi_column:
        print("布局检测为单栏，使用默认提取方式。")
        # 对单栏布局，简单按垂直、水平位置排序即可
        sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
        return " ".join(w['text'] for w in sorted_words)

    print(f"布局检测为 {n_columns} 栏，开始处理...")

    # 6. 定义列之间的分割点
    # 分割点是相邻列中心的中点
    split_points = [0] + [(column_centers[i] + column_centers[i + 1]) / 2 for i in range(len(column_centers) - 1)] + [
        page.width]

    # 7. 裁剪每一列并分别提取文本
    all_text_columns = []
    for i in range(n_columns):
        # 定义当前列的裁剪框 (x0, top, x1, bottom)
        col_bbox = (split_points[i], page.bbox[1], split_points[i + 1], page.bbox[3])

        # 将页面裁剪成单列
        column_page = page.crop(col_bbox)

        # 在裁剪后的单列页面上提取文本
        col_text = column_page.extract_text(x_tolerance=3, y_tolerance=3)

        if col_text:
            all_text_columns.append(col_text)

    # 8. 按顺序合并所有列的文本
    return "\n\n".join(all_text_columns)


# --- 使用示例 ---
# 确保在 'user_files' 目录下有一个多栏的 PDF 文件，例如 patent2.pdf
pdf_path = "../examples/patent22.pdf"

try:
    with pdfplumber.open(pdf_path) as pdf:
        # 以第一页为例进行处理
        first_page = pdf.pages[0]

        print(f"--- 正在使用自动列检测处理文件: {pdf_path} ---")
        extracted_text = extract_text_from_multi_column_auto(first_page)

        print("\n--- 提取结果 ---")
        print(extracted_text)

except FileNotFoundError:
    print(f"错误: 文件未找到 {pdf_path}")
except ImportError:
    print("错误: 请确保已安装 scikit-learn 和 numpy (`pip install scikit-learn numpy`)")
except Exception as e:
    print(f"处理过程中发生错误: {e}")
