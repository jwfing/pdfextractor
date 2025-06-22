"""
图像处理器 - 负责图像提取和处理
"""

from typing import List
from loguru import logger

from ..config import ExtractionConfig
from ..models import ImageResult
from ..exceptions import ImageProcessingError


class ImageProcessor:
    """图像处理器"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
    
    def extract_images(self, page_data, page_num: int) -> List[ImageResult]:
        """提取图像"""
        try:
            logger.info(f"图像提取第 {page_num} 页")
            
            images = []
            
            # 处理从PDF中提取的图像数据
            for image_data in page_data.images:
                image_result = self._process_image_data(image_data, page_num)
                if image_result:
                    images.append(image_result)
            
            return images
            
        except Exception as e:
            logger.error(f"图像提取失败: {e}")
            raise ImageProcessingError(f"图像提取失败: {e}")
    
    def _process_image_data(self, image_data: dict, page_num: int) -> ImageResult:
        """处理图像数据"""
        try:
            bbox = image_data.get('bbox', [0, 0, 0, 0])
            width = image_data.get('width', 0)
            height = image_data.get('height', 0)
            image_type = image_data.get('type', 'image')
            
            return ImageResult(
                image_path="",  # 暂时为空
                bbox=bbox,
                page_number=page_num,
                image_type=image_type
            )
            
        except Exception as e:
            logger.warning(f"处理图像数据失败: {e}")
            return None 