"""
export.py - 내보내기 API 라우터
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Literal
import base64
import io

from app.services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["Export"])


class FrameData(BaseModel):
    """프레임 데이터"""
    frame_number: int
    image_data: str  # Base64


class SpritesheetRequest(BaseModel):
    """스프라이트시트 요청"""
    frames: List[FrameData]
    frame_width: Optional[int] = None  # None이면 원본 크기
    frame_height: Optional[int] = None
    columns: int = 5
    padding: int = 0
    background_color: Optional[str] = None  # None이면 투명


class GifRequest(BaseModel):
    """GIF 요청"""
    frames: List[FrameData]
    fps: int = 12
    loop: int = 0  # 0 = 무한 반복
    width: Optional[int] = None
    height: Optional[int] = None
    background_color: Optional[str] = None  # None이면 투명


class PngSequenceRequest(BaseModel):
    """PNG 시퀀스 요청"""
    frames: List[FrameData]
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    prefix: str = "frame"


@router.post("/spritesheet")
async def export_spritesheet(request: SpritesheetRequest):
    """
    스프라이트시트 생성
    
    - **frames**: 프레임 데이터 배열 (frame_number, image_data)
    - **frame_width**: 각 프레임 너비 (px)
    - **frame_height**: 각 프레임 높이 (px)
    - **columns**: 열 개수
    - **padding**: 프레임 간 패딩 (px)
    - **background_color**: 배경색 (hex)
    """
    if not request.frames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프레임 데이터가 필요합니다.",
        )
    
    try:
        export_service = ExportService()
        
        # 프레임 이미지 디코딩
        frame_images = []
        for frame in sorted(request.frames, key=lambda f: f.frame_number):
            image_bytes = base64.b64decode(frame.image_data.split(",")[-1])
            frame_images.append(image_bytes)
        
        # 스프라이트시트 생성
        spritesheet = await export_service.create_spritesheet(
            frames=frame_images,
            frame_width=request.frame_width,
            frame_height=request.frame_height,
            columns=request.columns,
            padding=request.padding,
            background_color=request.background_color,
        )
        
        # Base64 인코딩
        buffered = io.BytesIO()
        spritesheet.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "image": img_base64,
            "width": spritesheet.width,
            "height": spritesheet.height,
            "frame_count": len(frame_images),
            "columns": request.columns,
            "rows": (len(frame_images) + request.columns - 1) // request.columns,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스프라이트시트 생성 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/gif")
async def export_gif(request: GifRequest):
    """
    GIF 생성
    
    - **frames**: 프레임 데이터 배열
    - **fps**: 초당 프레임 수
    - **loop**: 반복 횟수 (0 = 무한)
    - **width**: GIF 너비
    - **height**: GIF 높이
    - **background_color**: 배경색
    """
    if not request.frames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프레임 데이터가 필요합니다.",
        )
    
    try:
        export_service = ExportService()
        
        # 프레임 이미지 디코딩
        frame_images = []
        for frame in sorted(request.frames, key=lambda f: f.frame_number):
            image_bytes = base64.b64decode(frame.image_data.split(",")[-1])
            frame_images.append(image_bytes)
        
        # GIF 생성
        gif_data = await export_service.create_gif(
            frames=frame_images,
            fps=request.fps,
            loop=request.loop,
            width=request.width,
            height=request.height,
            background_color=request.background_color,
        )
        
        # Base64 인코딩
        gif_base64 = base64.b64encode(gif_data).decode()
        
        return {
            "gif": gif_base64,
            "frame_count": len(frame_images),
            "fps": request.fps,
            "duration_ms": len(frame_images) * (1000 // request.fps),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GIF 생성 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/png-sequence")
async def export_png_sequence(request: PngSequenceRequest):
    """
    PNG 시퀀스 생성 (ZIP 파일로 반환)
    
    - **frames**: 프레임 데이터 배열
    - **frame_width**: 각 프레임 너비
    - **frame_height**: 각 프레임 높이
    - **prefix**: 파일명 접두사
    """
    if not request.frames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프레임 데이터가 필요합니다.",
        )
    
    try:
        export_service = ExportService()
        
        # 프레임 이미지 디코딩
        frame_images = []
        for frame in sorted(request.frames, key=lambda f: f.frame_number):
            image_bytes = base64.b64decode(frame.image_data.split(",")[-1])
            frame_images.append(image_bytes)
        
        # PNG 시퀀스 (ZIP) 생성
        zip_data = await export_service.create_png_sequence(
            frames=frame_images,
            frame_width=request.frame_width,
            frame_height=request.frame_height,
            prefix=request.prefix,
        )
        
        # Base64 인코딩
        zip_base64 = base64.b64encode(zip_data).decode()
        
        return {
            "zip": zip_base64,
            "frame_count": len(frame_images),
            "prefix": request.prefix,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PNG 시퀀스 생성 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/spritesheet/download")
async def download_spritesheet(request: SpritesheetRequest):
    """
    스프라이트시트 직접 다운로드
    """
    if not request.frames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프레임 데이터가 필요합니다.",
        )
    
    try:
        export_service = ExportService()
        
        # 프레임 이미지 디코딩
        frame_images = []
        for frame in sorted(request.frames, key=lambda f: f.frame_number):
            image_bytes = base64.b64decode(frame.image_data.split(",")[-1])
            frame_images.append(image_bytes)
        
        # 스프라이트시트 생성
        spritesheet = await export_service.create_spritesheet(
            frames=frame_images,
            frame_width=request.frame_width,
            frame_height=request.frame_height,
            columns=request.columns,
            padding=request.padding,
            background_color=request.background_color,
        )
        
        # 스트리밍 응답
        buffered = io.BytesIO()
        spritesheet.save(buffered, format="PNG")
        buffered.seek(0)
        
        return StreamingResponse(
            buffered,
            media_type="image/png",
            headers={
                "Content-Disposition": "attachment; filename=spritesheet.png"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스프라이트시트 생성 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/gif/download")
async def download_gif(request: GifRequest):
    """
    GIF 직접 다운로드
    """
    if not request.frames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프레임 데이터가 필요합니다.",
        )
    
    try:
        export_service = ExportService()
        
        # 프레임 이미지 디코딩
        frame_images = []
        for frame in sorted(request.frames, key=lambda f: f.frame_number):
            image_bytes = base64.b64decode(frame.image_data.split(",")[-1])
            frame_images.append(image_bytes)
        
        # GIF 생성
        gif_data = await export_service.create_gif(
            frames=frame_images,
            fps=request.fps,
            loop=request.loop,
            width=request.width,
            height=request.height,
            background_color=request.background_color,
        )
        
        return StreamingResponse(
            io.BytesIO(gif_data),
            media_type="image/gif",
            headers={
                "Content-Disposition": "attachment; filename=animation.gif"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GIF 생성 중 오류가 발생했습니다: {str(e)}",
        )
