import logging
import math
from typing import List

import pdfplumber
import numpy as np
from sklearn.cluster import KMeans
import warnings

from sklearn.metrics import silhouette_score

logging.getLogger("pdfminer.pdfpage").setLevel(logging.ERROR)

class AdaptivePlumberExtractor:
    def __init__(self):
        self.min_words_limit = 20
        self.silhouette_score_threshold = 0.5
        self.column_threshold = 0.3  # 列间距阈值

    def extract_text(self, pdf_path: str, max_columns: int = 2) -> str:
        with pdfplumber.open(pdf_path) as pdf:
            extract_texts = []
            double_column_layout = self._is_multi_column_layout(pdf.pages)
            max_columns = 2 if double_column_layout else 1
            print(f"Recognized multi-column layout: {double_column_layout}, max_columns: {max_columns}")
#            for page in pdf.pages:
            if pdf.pages and len(pdf.pages) > 0:
                page = pdf.pages[0]
                extract_texts.append(self._extract_text_from_multi_column_auto(page, max_columns))
            return "\n\n".join(extract_texts)


    def _is_multi_column_layout(self, pages: List[pdfplumber.page.Page]) -> bool:
        num_pages = len(pages)
        target_num = 3
        if num_pages <= 1:
            target_num = 0
        elif num_pages <= 4:
            target_num = math.ceil(num_pages / 2)
        try:
            is_double_column = bool(pages[target_num].extract_table(dict(vertical_strategy='text', text_tolerance=12)))
            print(f"num_pages: {num_pages}, target_num: {target_num}, is_double_column: {is_double_column}")
        except Exception as e:
            print(f"error : {str(e)}")
            is_double_column = False
        return is_double_column


    def _extract_text_from_multi_column_auto(self, page: pdfplumber.page.Page, max_columns: int = 2) -> str:
        """
        使用 K-Means 聚类和轮廓系数自动检测并提取多栏页面的文本。

        Args:
            page: 一个 pdfplumber.page.Page 对象。
            max_columns: 考虑的最大列数，默认为 3。函数将自动从 1 到 max_columns 中选择最佳列数。

        Returns:
            提取并正确排序后的文本。
        """
        # 1. 获取单词
        words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False)

        if not words or max_columns < 2:
            return page.extract_text() or ""

        # 如果单词太少，很可能是单栏或者空页面，直接默认处理
        if len(words) < self.min_words_limit:
            print("单词数量过少，使用默认单栏提取方式。")
            # 使用 extract_text 并设置容差，比手动排序单词更稳健
            return page.extract_text(x_tolerance=3, y_tolerance=3) or ""

        # 2. 准备聚类数据
        x_centers = np.array([(word['x0'] + word['x1']) / 2 for word in words]).reshape(-1, 1)

        # 3. 寻找最佳列数 (k)
        # 我们测试从 2 到 max_columns 的每一种可能性，并用轮廓系数评估效果。
        # 轮廓系数不能用于 k=1 的情况，所以我们从 k=2 开始。
        scores = {}
        # 确保测试的列数不超过 (单词数 - 1)
        actual_max_columns = min(max_columns, len(x_centers) - 1)

        if actual_max_columns >= 2:
            for k in range(2, actual_max_columns + 1):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10).fit(x_centers)

                # 确保形成了多个簇，才能计算轮廓系数
                if len(set(kmeans.labels_)) > 1:
                    score = silhouette_score(x_centers, kmeans.labels_)
                    scores[k] = score
                    print(f"测试 {k} 栏布局, 轮廓系数: {score:.4f}")
                else:
                    # 如果所有点都被分到同一个簇，说明不适合多栏
                    scores[k] = -1  # 给一个很差的分数

        # 如果没有任何多栏布局得分，或者最高分很低，我们倾向于它是单栏
        # 这里我们选择得分最高的 k 值作为候选
        if scores:
            best_k = max(scores, key=scores.get)
            # 如果最高分都小于0，说明聚类效果很差，很可能是单栏
            if scores[best_k] < self.silhouette_score_threshold:  # 可以调整这个阈值
                best_k = 1
        else:
            best_k = 1

        # 4. 如果最佳候选是单栏，直接按单栏处理
        if best_k == 1:
            print("布局检测为单栏，使用默认提取方式。")
            sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
            return " ".join(w['text'] for w in sorted_words)

        # 5. 对最佳的多栏候选 (best_k > 1)，进行最终的合理性检查
        print(f"最佳列数候选: {best_k}，进行合理性检查...")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10).fit(x_centers)

        column_centers = sorted(kmeans.cluster_centers_.flatten())
        print(f"column_centers: {column_centers}")
        # 检查列中心是否靠得太近
        min_separation = page.width * self.column_threshold
        print(f"min_separation: {min_separation}")

        is_well_separated = True
        if len(column_centers) > 1:
            for i in range(len(column_centers) - 1):
                if (column_centers[i + 1] - column_centers[i]) < min_separation:
                    is_well_separated = False
                    break
        else:
            is_well_separated = False

        # 如果检查不通过，回退到单栏模式
        if not is_well_separated:
            print("多栏检测结果不显著 (列间距过小)，回退至单栏提取方式。")
            sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
            return " ".join(w['text'] for w in sorted_words)

        # 6. 如果所有检查都通过，则按检测到的多栏布局进行处理
        n_columns = best_k
        print(f"布局检测为 {n_columns} 栏，开始处理...")

        split_points = [0] + [(column_centers[i] + column_centers[i + 1]) / 2 for i in range(len(column_centers) - 1)] + [
            page.width]

        all_text_columns = []
        for i in range(n_columns):
            col_bbox = (split_points[i], page.bbox[1], split_points[i + 1], page.bbox[3])
            column_page = page.crop(col_bbox)
            col_text = column_page.extract_text(x_tolerance=3, y_tolerance=3)
            if col_text:
                all_text_columns.append(col_text)

        return "\n\n".join(all_text_columns)
