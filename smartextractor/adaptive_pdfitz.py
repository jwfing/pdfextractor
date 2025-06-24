import logging

import fitz  # PyMuPDF
import numpy as np
from collections import defaultdict
from typing import List, Dict, Tuple
import warnings  # Import warnings to suppress KMeans warnings

logger = logging.getLogger(__name__)

class AdaptiveFitzExtractor:
    def __init__(self):
        self.column_threshold = 0.3  # 列间距阈值
        self.min_column_width = 0.25  # 最小列宽比例

    def extract_text(self, pdf_path: str) -> str:
        """主提取函数"""
        doc = fitz.open(pdf_path)
        full_text = []

        # for page_num in range(doc.page_count):
        if doc.page_count > 0:
            page_num = 0
            page = doc[page_num]
            page_text = self._extract_page_text(page)
            if page_text:
                full_text.append(page_text)

        doc.close()
        return '\n\n'.join(full_text)

    def _extract_page_text(self, page) -> str:
        """提取单页文本"""
        # 获取文本块
        blocks = self._get_text_blocks(page)
        if not blocks:
            return ""

        # 检测布局类型
        layout_type = self._detect_layout_type(blocks, page.rect.width)
        logger.debug(f"layout_type: {layout_type}")
        print(f"layout_type: {layout_type}")

        if layout_type == "single_column":
            return self._extract_single_column(blocks)
        else:
            return self._extract_multi_column(blocks, page.rect.width)

    def _get_text_blocks(self, page) -> List[Dict]:
        """获取并处理文本块"""
        blocks = []
        text_dict = page.get_text("dict")

        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue

            # 合并文本块内容
            block_text = ""
            for line in block["lines"]:
                line_text = ""
                for span in line["spans"]:
                    line_text += span["text"]
                block_text += line_text + "\n"

            if block_text.strip():
                blocks.append({
                    'text': block_text.strip(),
                    'bbox': block["bbox"],
                    'x0': block["bbox"][0],
                    'y0': block["bbox"][1],
                    'x1': block["bbox"][2],
                    'y1': block["bbox"][3],
                    'width': block["bbox"][2] - block["bbox"][0],
                    'height': block["bbox"][3] - block["bbox"][1]
                })

        return blocks

    def _detect_layout_type(self, blocks: List[Dict], page_width: float) -> str:
        """检测布局类型：单列或多列"""
        if len(blocks) < 2:
            return "single_column"

        # 方法1: 基于文本块x坐标分布
        x_positions = [block['x0'] for block in blocks]
        x_centers = [(block['x0'] + block['x1']) / 2 for block in blocks]

        # 使用K-means聚类检测列数
        column_centers = self._detect_columns_kmeans(x_centers, page_width)

        # 只有当_detect_columns_kmeans明确检测到两列时，才认为它是多列
        if len(column_centers) >= 2:
            # 检查是否有明显的列间距 (这个检查可以作为辅助，但主要依赖聚类结果)
            if self._has_clear_column_gap(blocks, page_width):
                return "multi_column"
            else:
                # 如果聚类检测到两列但没有明显的物理间距，可能不是标准双栏
                logger.debug("KMeans detected two columns but no clear gap. Might be single column with wide text.")

        # 方法2: 基于文本块宽度分析 (作为辅助判断)
        avg_width = np.mean([block['width'] for block in blocks])
        # 如果平均宽度小于页面宽度的60%，且没有被明确判断为单列，则可能是多列
        if avg_width < page_width * 0.6 and len(column_centers) < 2:  # 避免与方法1冲突
            logger.debug(
                f"Layout detected as multi_column based on average block width ({avg_width:.2f} < {page_width * 0.6:.2f})")
            return "multi_column"

        return "single_column"

    def _detect_columns_kmeans(self, x_centers: List[float], page_width: float) -> List[float]:
        """
        使用聚类检测列中心。
        如果能自信地检测到两列，则返回两个列中心的列表；否则返回空列表。
        """
        if len(x_centers) < 2:
            return []  # 数据不足，无法检测多列

        x_centers_np = np.array(x_centers).reshape(-1, 1)

        # 尝试2列K-Means聚类
        try:
            from sklearn.cluster import KMeans
            # 抑制 KMeans 的 n_init 警告
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
                clusters = kmeans.fit_predict(x_centers_np)
                centers = kmeans.cluster_centers_.flatten()

            # 检查聚类质量：确保形成了两个不同的簇，并且它们之间有足够的距离
            if len(set(clusters)) == 2:  # 确保确实分成了两类
                center_distance = abs(centers[1] - centers[0])
                # 列中心距离应大于页面宽度的20%才认为是两列
                if center_distance > page_width * 0.2:
                    return sorted(centers)
        except ImportError:
            logger.debug("scikit-learn not installed, falling back to histogram method for column detection.")
        except Exception as e:  # 捕获其他 KMeans 错误，例如数据退化
            logger.debug(f"KMeans failed: {e}, falling back to histogram method.")

        # 备用方案：简单的直方图峰值检测 (改进版)
        # 使用更细的 bin 来提高分辨率
        hist, bins = np.histogram(x_centers, bins=50)  # 增加 bin 数量

        # 寻找峰值：一个峰值比其相邻点高，且高于整体最大值的某个比例
        peaks = []
        for i in range(1, len(hist) - 1):
            if hist[i] > hist[i - 1] and hist[i] > hist[i + 1] and hist[i] > np.max(hist) * 0.1:  # 降低峰值检测阈值
                peaks.append((bins[i] + bins[i + 1]) / 2)

        # 过滤峰值，寻找两个足够分离的峰值作为列中心
        if len(peaks) >= 2:
            sorted_peaks = sorted(peaks)

            # 检查最左和最右的峰值是否足够分离
            if (sorted_peaks[-1] - sorted_peaks[0]) > page_width * 0.2:
                # 如果有多个峰值，取最左和最右的作为潜在列中心
                return [sorted_peaks[0], sorted_peaks[-1]]
            elif len(sorted_peaks) >= 2:  # 如果不远，但仍有两个峰值，取前两个
                return sorted_peaks[:2]

        return []  # 如果无法自信地检测到两列，返回空列表

    def _has_clear_column_gap(self, blocks: List[Dict], page_width: float) -> bool:
        """检测是否有明显的列间距"""
        # 在页面中央区域寻找空白区域
        center_start = page_width * 0.3
        center_end = page_width * 0.7

        # 检查是否有文本块横跨中央区域
        for block in blocks:
            if (block['x0'] < center_start and block['x1'] > center_end):
                return False

        # 检查中央区域的文本密度
        center_blocks = [block for block in blocks
                         if block['x0'] >= center_start and block['x1'] <= center_end]

        return len(center_blocks) < len(blocks) * 0.2

    def _extract_single_column(self, blocks: List[Dict]) -> str:
        """提取单列文本"""
        # 按y坐标排序
        blocks.sort(key=lambda x: x['y0'])
        return '\n'.join([block['text'] for block in blocks])

    def _extract_multi_column(self, blocks: List[Dict], page_width: float) -> str:
        """提取多列文本"""
        logger.debug(f"enter _extract_multi_column with page_width: {page_width}")

        x_centers = [(block['x0'] + block['x1']) / 2 for block in blocks]
        column_centers = self._detect_columns_kmeans(x_centers, page_width)

        split_point = page_width / 2  # 默认分割点，如果无法通过更精确方法确定

        if len(column_centers) >= 2:
            # 如果自信地检测到两个列中心，使用它们的中间点作为分割点
            split_point = (column_centers[0] + column_centers[1]) / 2
            logger.debug(f"KMeans/Histogram detected split_point: {split_point:.2f}")
        else:
            # 备用方案：如果聚类未能找到两列，尝试寻找文本块之间的最大水平间隙
            # 这对于 _detect_layout_type 基于 avg_width 判断为多列但聚类失败的情况尤其重要

            # 收集所有文本块的 x0 和 x1 坐标
            x_coords = sorted([block['x0'] for block in blocks] + [block['x1'] for block in blocks])

            max_gap = 0
            potential_split_point = page_width / 2  # 备用分割点，如果未找到显著间隙

            # 遍历排序后的 x 坐标，寻找最大的间隙
            for i in range(len(x_coords) - 1):
                gap = x_coords[i + 1] - x_coords[i]
                # 仅考虑页面中央区域的间隙，避免边缘的空白
                if gap > max_gap and page_width * 0.3 < x_coords[i] < page_width * 0.7:
                    max_gap = gap
                    potential_split_point = (x_coords[i] + x_coords[i + 1]) / 2

            # 如果找到一个显著的间隙，则使用它作为分割点
            # 显著性定义：间隙宽度大于页面宽度的5%
            if max_gap > page_width * 0.05:
                split_point = potential_split_point
                logger.debug(f"Largest gap detected split_point: {split_point:.2f} (max_gap: {max_gap:.2f})")
            else:
                logger.debug(f"No significant gap found, using default split_point: {split_point:.2f}")

        # 根据确定的分割点将文本块分配到左右列
        left_blocks = []
        right_blocks = []

        for block in blocks:
            block_center = (block['x0'] + block['x1']) / 2
            if block_center < split_point:
                left_blocks.append(block)
            else:
                right_blocks.append(block)

        # 按y坐标排序
        left_blocks.sort(key=lambda x: x['y0'])
        right_blocks.sort(key=lambda x: x['y0'])

        # 合并文本（先左列，再右列）
        result = []
        if left_blocks:
            result.extend([block['text'] for block in left_blocks])
        if right_blocks:
            result.extend([block['text'] for block in right_blocks])

        return '\n'.join(result)


# 使用示例
def extract_adaptive_text(pdf_path: str) -> str:
    extractor = AdaptiveFitzExtractor()
    return extractor.extract_text(pdf_path)