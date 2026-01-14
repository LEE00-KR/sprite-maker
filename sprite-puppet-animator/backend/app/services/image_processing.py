"""
image_processing.py - 이미지 처리 서비스
"""

from PIL import Image
import numpy as np
import cv2
import io
from typing import Tuple, Optional
import asyncio


class ImageProcessor:
    """이미지 처리 서비스"""
    
    async def remove_background(
        self,
        image_data: bytes,
        tolerance: int = 30,
        edge_smoothing: int = 2,
    ) -> Image.Image:
        """
        배경 제거
        
        Args:
            image_data: 이미지 바이트 데이터
            tolerance: 배경색 허용 오차 (0-100)
            edge_smoothing: 엣지 부드러움 정도 (0-10)
        
        Returns:
            배경이 제거된 PIL Image
        """
        # 이미지 로드
        image = Image.open(io.BytesIO(image_data)).convert("RGBA")
        
        # rembg 라이브러리 사용 시도
        try:
            from rembg import remove
            
            # rembg로 배경 제거
            result = await asyncio.to_thread(remove, image_data)
            result_image = Image.open(io.BytesIO(result)).convert("RGBA")
            
            # 엣지 스무딩 적용
            if edge_smoothing > 0:
                result_image = self._smooth_edges(result_image, edge_smoothing)
            
            return result_image
            
        except ImportError:
            # rembg가 없으면 간단한 색상 기반 제거
            return self._remove_background_by_color(image, tolerance, edge_smoothing)
    
    def _remove_background_by_color(
        self,
        image: Image.Image,
        tolerance: int,
        edge_smoothing: int,
    ) -> Image.Image:
        """색상 기반 배경 제거 (간단한 방법)"""
        # numpy 배열로 변환
        img_array = np.array(image)
        
        # 모서리 픽셀들의 색상을 배경색으로 추정
        corners = [
            img_array[0, 0],
            img_array[0, -1],
            img_array[-1, 0],
            img_array[-1, -1],
        ]
        bg_color = np.median(corners, axis=0).astype(np.uint8)
        
        # 배경색과의 차이 계산
        diff = np.abs(img_array[:, :, :3].astype(np.int16) - bg_color[:3].astype(np.int16))
        diff_sum = np.sum(diff, axis=2)
        
        # 마스크 생성
        threshold = tolerance * 3  # RGB 합계 기준
        mask = diff_sum > threshold
        
        # 알파 채널 적용
        result = img_array.copy()
        result[:, :, 3] = (mask * 255).astype(np.uint8)
        
        result_image = Image.fromarray(result)
        
        # 엣지 스무딩
        if edge_smoothing > 0:
            result_image = self._smooth_edges(result_image, edge_smoothing)
        
        return result_image
    
    def _smooth_edges(self, image: Image.Image, amount: int) -> Image.Image:
        """엣지 스무딩"""
        # 알파 채널 추출
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        r, g, b, a = image.split()
        
        # OpenCV로 블러 처리
        alpha_array = np.array(a)
        kernel_size = amount * 2 + 1
        blurred = cv2.GaussianBlur(alpha_array, (kernel_size, kernel_size), 0)
        
        # 다시 합치기
        a_smooth = Image.fromarray(blurred)
        return Image.merge("RGBA", (r, g, b, a_smooth))
    
    async def cut_region(
        self,
        image_data: bytes,
        mask_data: bytes,
    ) -> Tuple[Image.Image, Image.Image]:
        """
        영역 오려내기
        
        Args:
            image_data: 원본 이미지 바이트
            mask_data: 마스크 이미지 바이트 (흰색 = 선택 영역)
        
        Returns:
            (오려낸 이미지, 남은 이미지) 튜플
        """
        # 이미지 로드
        image = Image.open(io.BytesIO(image_data)).convert("RGBA")
        mask = Image.open(io.BytesIO(mask_data)).convert("L")
        
        # 마스크 크기 조정
        if mask.size != image.size:
            mask = mask.resize(image.size, Image.LANCZOS)
        
        img_array = np.array(image)
        mask_array = np.array(mask)
        
        # 오려낸 이미지 (마스크 영역만)
        cut_array = img_array.copy()
        cut_array[:, :, 3] = np.minimum(cut_array[:, :, 3], mask_array)
        
        # 남은 이미지 (마스크 영역 제외)
        remaining_array = img_array.copy()
        inverted_mask = 255 - mask_array
        remaining_array[:, :, 3] = np.minimum(remaining_array[:, :, 3], inverted_mask)
        
        return Image.fromarray(cut_array), Image.fromarray(remaining_array)
    
    async def fill_region(
        self,
        image_data: bytes,
        mask_data: bytes,
        method: str = "average",
    ) -> Image.Image:
        """
        영역 채우기
        
        Args:
            image_data: 원본 이미지 바이트
            mask_data: 마스크 이미지 바이트 (흰색 = 채울 영역)
            method: 채우기 방법 ("average", "clone", "content_aware")
        
        Returns:
            채워진 이미지
        """
        # 이미지 로드
        image = Image.open(io.BytesIO(image_data)).convert("RGBA")
        mask = Image.open(io.BytesIO(mask_data)).convert("L")
        
        # 마스크 크기 조정
        if mask.size != image.size:
            mask = mask.resize(image.size, Image.LANCZOS)
        
        if method == "average":
            return self._fill_average(image, mask)
        elif method == "clone":
            return self._fill_inpaint(image, mask)
        elif method == "content_aware":
            return self._fill_inpaint(image, mask)
        else:
            return self._fill_average(image, mask)
    
    def _fill_average(self, image: Image.Image, mask: Image.Image) -> Image.Image:
        """평균 색상으로 채우기"""
        img_array = np.array(image)
        mask_array = np.array(mask)
        
        # 마스크 주변 픽셀의 평균 색상 계산
        dilated = cv2.dilate(mask_array, np.ones((5, 5), np.uint8), iterations=3)
        border_mask = dilated - mask_array
        
        # 주변 픽셀 추출
        border_pixels = img_array[border_mask > 128]
        
        if len(border_pixels) > 0:
            avg_color = np.mean(border_pixels, axis=0).astype(np.uint8)
        else:
            avg_color = np.array([128, 128, 128, 255], dtype=np.uint8)
        
        # 채우기
        result = img_array.copy()
        result[mask_array > 128] = avg_color
        
        return Image.fromarray(result)
    
    def _fill_inpaint(self, image: Image.Image, mask: Image.Image) -> Image.Image:
        """OpenCV Inpainting으로 채우기"""
        # RGB로 변환 (OpenCV inpaint는 RGB만 지원)
        img_rgb = image.convert("RGB")
        img_array = np.array(img_rgb)
        mask_array = np.array(mask)
        
        # BGR로 변환
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Inpainting
        result_bgr = cv2.inpaint(img_bgr, mask_array, 3, cv2.INPAINT_TELEA)
        
        # RGB로 다시 변환
        result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
        
        # 원본 알파 채널 복원
        result = Image.fromarray(result_rgb).convert("RGBA")
        if image.mode == "RGBA":
            r, g, b, _ = result.split()
            _, _, _, a = image.split()
            result = Image.merge("RGBA", (r, g, b, a))
        
        return result
    
    async def resize(
        self,
        image_data: bytes,
        width: Optional[int] = None,
        height: Optional[int] = None,
        maintain_aspect: bool = True,
    ) -> Image.Image:
        """이미지 크기 조정"""
        image = Image.open(io.BytesIO(image_data))
        
        if width is None and height is None:
            return image
        
        orig_width, orig_height = image.size
        
        if maintain_aspect:
            if width and height:
                ratio = min(width / orig_width, height / orig_height)
                new_width = int(orig_width * ratio)
                new_height = int(orig_height * ratio)
            elif width:
                ratio = width / orig_width
                new_width = width
                new_height = int(orig_height * ratio)
            else:
                ratio = height / orig_height
                new_width = int(orig_width * ratio)
                new_height = height
        else:
            new_width = width or orig_width
            new_height = height or orig_height
        
        return image.resize((new_width, new_height), Image.LANCZOS)
    
    async def create_thumbnail(
        self,
        image_data: bytes,
        size: int = 128,
    ) -> Image.Image:
        """썸네일 생성"""
        image = Image.open(io.BytesIO(image_data))
        image.thumbnail((size, size), Image.LANCZOS)
        return image
