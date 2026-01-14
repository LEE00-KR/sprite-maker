"""
image.py - 이미지 처리 API 라우터
"""

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional
import base64
import io

from app.services.image_processing import ImageProcessor

router = APIRouter(prefix="/image", tags=["Image Processing"])


@router.post("/remove-background")
async def remove_background(
    image: UploadFile = File(...),
    tolerance: int = Form(30),
    edge_smoothing: int = Form(2),
):
    """
    이미지 배경 제거
    
    - **image**: 이미지 파일 (PNG, JPG, JPEG, WEBP)
    - **tolerance**: 배경색 허용 오차 (0-100)
    - **edge_smoothing**: 엣지 부드러움 정도 (0-10)
    """
    # 파일 유효성 검사
    if not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미지 파일만 업로드 가능합니다.",
        )
    
    try:
        # 이미지 읽기
        image_data = await image.read()
        
        # 배경 제거
        processor = ImageProcessor()
        result_image = await processor.remove_background(
            image_data,
            tolerance=tolerance,
            edge_smoothing=edge_smoothing,
        )
        
        # Base64 인코딩
        buffered = io.BytesIO()
        result_image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "image": img_base64,
            "width": result_image.width,
            "height": result_image.height,
            "message": "배경이 제거되었습니다.",
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"이미지 처리 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/cut-layer")
async def cut_layer(
    image_data: str,
    mask: str,
):
    """
    이미지에서 영역을 오려내어 새 레이어로 분리
    
    - **image_data**: Base64 인코딩된 이미지
    - **mask**: Base64 인코딩된 마스크 (선택 영역)
    """
    try:
        processor = ImageProcessor()
        
        # Base64 디코딩
        image_bytes = base64.b64decode(image_data.split(",")[-1])
        mask_bytes = base64.b64decode(mask.split(",")[-1])
        
        # 오려내기
        cut_image, remaining_image = await processor.cut_region(
            image_bytes, 
            mask_bytes
        )
        
        # Base64 인코딩
        cut_buffered = io.BytesIO()
        cut_image.save(cut_buffered, format="PNG")
        cut_base64 = base64.b64encode(cut_buffered.getvalue()).decode()
        
        remaining_buffered = io.BytesIO()
        remaining_image.save(remaining_buffered, format="PNG")
        remaining_base64 = base64.b64encode(remaining_buffered.getvalue()).decode()
        
        return {
            "cut_layer": cut_base64,
            "remaining_layer": remaining_base64,
            "message": "레이어가 분리되었습니다.",
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"레이어 분리 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/fill")
async def fill_region(
    image_data: str,
    mask: str,
    fill_method: str = "average",  # "average", "clone", "content_aware"
):
    """
    선택 영역을 주변 색상으로 채우기
    
    - **image_data**: Base64 인코딩된 이미지
    - **mask**: Base64 인코딩된 마스크 (채울 영역)
    - **fill_method**: 채우기 방법 (average: 평균색, clone: 복제, content_aware: 내용 인식)
    """
    try:
        processor = ImageProcessor()
        
        # Base64 디코딩
        image_bytes = base64.b64decode(image_data.split(",")[-1])
        mask_bytes = base64.b64decode(mask.split(",")[-1])
        
        # 채우기
        filled_image = await processor.fill_region(
            image_bytes,
            mask_bytes,
            method=fill_method,
        )
        
        # Base64 인코딩
        buffered = io.BytesIO()
        filled_image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "image": img_base64,
            "message": "영역이 채워졌습니다.",
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"채우기 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/resize")
async def resize_image(
    image_data: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    maintain_aspect: bool = True,
):
    """
    이미지 크기 조정
    """
    try:
        processor = ImageProcessor()
        
        # Base64 디코딩
        image_bytes = base64.b64decode(image_data.split(",")[-1])
        
        # 리사이즈
        resized = await processor.resize(
            image_bytes,
            width=width,
            height=height,
            maintain_aspect=maintain_aspect,
        )
        
        # Base64 인코딩
        buffered = io.BytesIO()
        resized.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "image": img_base64,
            "width": resized.width,
            "height": resized.height,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"크기 조정 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/create-thumbnail")
async def create_thumbnail(
    image_data: str,
    size: int = 128,
):
    """
    썸네일 생성
    """
    try:
        processor = ImageProcessor()
        
        # Base64 디코딩
        image_bytes = base64.b64decode(image_data.split(",")[-1])
        
        # 썸네일 생성
        thumbnail = await processor.create_thumbnail(image_bytes, size)
        
        # Base64 인코딩
        buffered = io.BytesIO()
        thumbnail.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "thumbnail": img_base64,
            "size": size,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"썸네일 생성 중 오류가 발생했습니다: {str(e)}",
        )
