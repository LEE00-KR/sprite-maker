"""
export_service.py - 내보내기 서비스
"""

from PIL import Image
import numpy as np
import io
import zipfile
from typing import List, Optional, Tuple
import imageio


class ExportService:
    """내보내기 서비스"""
    
    async def create_spritesheet(
        self,
        frames: List[bytes],
        frame_width: Optional[int] = None,
        frame_height: Optional[int] = None,
        columns: int = 5,
        padding: int = 0,
        background_color: Optional[str] = None,
    ) -> Image.Image:
        """
        스프라이트시트 생성
        
        Args:
            frames: 프레임 이미지 바이트 리스트
            frame_width: 각 프레임 너비 (None이면 원본)
            frame_height: 각 프레임 높이 (None이면 원본)
            columns: 열 개수
            padding: 프레임 간 패딩
            background_color: 배경색 (hex, None이면 투명)
        
        Returns:
            스프라이트시트 이미지
        """
        if not frames:
            raise ValueError("프레임이 없습니다.")
        
        # 프레임 이미지 로드
        frame_images = []
        for frame_data in frames:
            img = Image.open(io.BytesIO(frame_data)).convert("RGBA")
            frame_images.append(img)
        
        # 프레임 크기 결정
        if frame_width is None or frame_height is None:
            # 첫 번째 프레임 크기 사용
            frame_width = frame_width or frame_images[0].width
            frame_height = frame_height or frame_images[0].height
        
        # 모든 프레임 리사이즈
        resized_frames = []
        for img in frame_images:
            if img.size != (frame_width, frame_height):
                img = img.resize((frame_width, frame_height), Image.LANCZOS)
            resized_frames.append(img)
        
        # 스프라이트시트 크기 계산
        frame_count = len(resized_frames)
        rows = (frame_count + columns - 1) // columns
        
        sheet_width = columns * frame_width + (columns - 1) * padding
        sheet_height = rows * frame_height + (rows - 1) * padding
        
        # 배경색 처리
        if background_color:
            bg = self._hex_to_rgba(background_color)
            spritesheet = Image.new("RGBA", (sheet_width, sheet_height), bg)
        else:
            spritesheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
        
        # 프레임 배치
        for i, frame in enumerate(resized_frames):
            col = i % columns
            row = i // columns
            
            x = col * (frame_width + padding)
            y = row * (frame_height + padding)
            
            spritesheet.paste(frame, (x, y), frame)
        
        return spritesheet
    
    async def create_gif(
        self,
        frames: List[bytes],
        fps: int = 12,
        loop: int = 0,
        width: Optional[int] = None,
        height: Optional[int] = None,
        background_color: Optional[str] = None,
    ) -> bytes:
        """
        GIF 생성
        
        Args:
            frames: 프레임 이미지 바이트 리스트
            fps: 초당 프레임 수
            loop: 반복 횟수 (0 = 무한)
            width: GIF 너비
            height: GIF 높이
            background_color: 배경색 (hex)
        
        Returns:
            GIF 바이트 데이터
        """
        if not frames:
            raise ValueError("프레임이 없습니다.")
        
        # 프레임 이미지 로드
        frame_images = []
        for frame_data in frames:
            img = Image.open(io.BytesIO(frame_data)).convert("RGBA")
            
            # 크기 조정
            if width and height:
                img = img.resize((width, height), Image.LANCZOS)
            elif width:
                ratio = width / img.width
                img = img.resize((width, int(img.height * ratio)), Image.LANCZOS)
            elif height:
                ratio = height / img.height
                img = img.resize((int(img.width * ratio), height), Image.LANCZOS)
            
            # 배경색 처리
            if background_color:
                bg = Image.new("RGBA", img.size, self._hex_to_rgba(background_color))
                bg.paste(img, (0, 0), img)
                img = bg
            
            # GIF는 P 모드 필요
            frame_images.append(img)
        
        # GIF 생성
        duration = 1000 // fps  # 밀리초
        
        output = io.BytesIO()
        
        # 첫 프레임
        first_frame = frame_images[0]
        
        # P 모드로 변환 (투명 GIF 지원)
        if background_color is None:
            # 투명 배경
            converted_frames = []
            for img in frame_images:
                # 투명도 처리
                alpha = img.getchannel('A')
                img = img.convert('P', palette=Image.ADAPTIVE, colors=255)
                
                # 투명 색상 인덱스 설정
                mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
                img.paste(255, mask)
                
                converted_frames.append(img)
            
            converted_frames[0].save(
                output,
                format='GIF',
                save_all=True,
                append_images=converted_frames[1:],
                duration=duration,
                loop=loop,
                transparency=255,
                disposal=2,  # 이전 프레임 지우기
            )
        else:
            # 불투명 배경
            rgb_frames = [img.convert('RGB') for img in frame_images]
            rgb_frames[0].save(
                output,
                format='GIF',
                save_all=True,
                append_images=rgb_frames[1:],
                duration=duration,
                loop=loop,
            )
        
        return output.getvalue()
    
    async def create_png_sequence(
        self,
        frames: List[bytes],
        frame_width: Optional[int] = None,
        frame_height: Optional[int] = None,
        prefix: str = "frame",
    ) -> bytes:
        """
        PNG 시퀀스 (ZIP 파일) 생성
        
        Args:
            frames: 프레임 이미지 바이트 리스트
            frame_width: 각 프레임 너비
            frame_height: 각 프레임 높이
            prefix: 파일명 접두사
        
        Returns:
            ZIP 파일 바이트 데이터
        """
        if not frames:
            raise ValueError("프레임이 없습니다.")
        
        output = io.BytesIO()
        
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, frame_data in enumerate(frames):
                img = Image.open(io.BytesIO(frame_data)).convert("RGBA")
                
                # 크기 조정
                if frame_width and frame_height:
                    img = img.resize((frame_width, frame_height), Image.LANCZOS)
                
                # PNG로 저장
                frame_buffer = io.BytesIO()
                img.save(frame_buffer, format='PNG')
                
                # ZIP에 추가
                filename = f"{prefix}_{i:04d}.png"
                zf.writestr(filename, frame_buffer.getvalue())
        
        return output.getvalue()
    
    def _hex_to_rgba(self, hex_color: str) -> Tuple[int, int, int, int]:
        """Hex 색상을 RGBA 튜플로 변환"""
        hex_color = hex_color.lstrip('#')
        
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (r, g, b, 255)
        elif len(hex_color) == 8:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            a = int(hex_color[6:8], 16)
            return (r, g, b, a)
        else:
            return (255, 255, 255, 255)
