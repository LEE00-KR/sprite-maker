import streamlit as st
import cv2
import numpy as np
import tempfile
import os
import zipfile
from PIL import Image
import io

# --- [로직은 기존과 동일] ---
def remove_background(image, target_color, tolerance):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    lower_bound = np.array([max(c - tolerance, 0) for c in target_color])
    upper_bound = np.array([min(c + tolerance, 255) for c in target_color])
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
    mask = cv2.inRange(rgb_image, lower_bound, upper_bound)
    mask_inv = cv2.bitwise_not(mask)
    image[:, :, 3] = mask_inv
    return image

def create_sprite_sheet(images):
    if not images: return None
    width, height = images[0].size
    total_width = width * len(images)
    sheet = Image.new("RGBA", (total_width, height))
    for idx, img in enumerate(images):
        sheet.paste(img, (idx * width, 0))
    return sheet

# --- [UI 설정] 모바일 최적화 ---
st.set_page_config(page_title="Sprite Maker", layout="centered") # 모바일은 centered가 더 깔끔함

st.header("🦖 스프라이트 생성기")
st.caption("비디오를 넣으면 투명 배경 스프라이트로 변환합니다.")

# 1. 파일 업로드 (가장 상단에 배치)
uploaded_file = st.file_uploader("1. 영상 파일 업로드 (MP4/MOV)", type=["mp4", "mov", "avi"])

if uploaded_file is not None:
    # 파일 임시 저장
    tfile = tempfile.NamedTemporaryFile(delete=False) 
    tfile.write(uploaded_file.read())
    cap = cv2.VideoCapture(tfile.name)
    
    # 첫 프레임 읽기 (미리보기 및 색상 추출용)
    ret, first_frame = cap.read()
    first_frame_rgb = None
    if ret:
        first_frame_rgb = cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)

    # 2. 설정 영역 (접이식으로 공간 절약)
    with st.expander("⚙️ 배경 제거 설정 (터치하여 열기)", expanded=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            bg_color_hex = st.color_picker("제거할 색상", "#000000")
        with col2:
            tolerance = st.slider("민감도", 0, 150, 60, help="비슷한 색을 어디까지 지울지 결정")
        
        # 원본 미리보기 작게 표시 (색상 비교용)
        if first_frame_rgb is not None:
            st.image(first_frame_rgb, caption="원본 첫 프레임", use_container_width=True)

    # Hex -> RGB 변환
    bg_color_rgb = tuple(int(bg_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

    # 3. 변환 버튼 (터치하기 좋게 크게)
    if st.button("✨ 변환 시작하기", type="primary", use_container_width=True):
        
        status_area = st.empty()
        status_area.info("영상을 프레임 단위로 쪼개는 중...")
        
        progress_bar = st.progress(0)
        processed_pil_images = []
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            processed_cv = remove_background(frame, bg_color_rgb, tolerance)
            processed_rgb = cv2.cvtColor(processed_cv, cv2.COLOR_BGRA2RGBA)
            pil_img = Image.fromarray(processed_rgb)
            processed_pil_images.append(pil_img)
            
            frame_count += 1
            if total_frames > 0:
                progress_bar.progress(min(frame_count / total_frames, 1.0))
        
        status_area.success("변환 완료! 아래 탭에서 확인하세요.")
        progress_bar.empty()

        # 4. 결과 화면 (탭 UI 사용 - 모바일 핵심)
        tab1, tab2 = st.tabs(["🎬 움직임 확인(GIF)", "📥 저장 및 시트"])
        
        # GIF 생성 (메모리)
        gif_buffer = io.BytesIO()
        processed_pil_images[0].save(
            gif_buffer, format="GIF", save_all=True, append_images=processed_pil_images[1:], 
            duration=100, loop=0, disposal=2, transparency=0
        )
        
        # 스프라이트 시트 생성 (메모리)
        sprite_sheet = create_sprite_sheet(processed_pil_images)
        sheet_buffer = io.BytesIO()
        sprite_sheet.save(sheet_buffer, format="PNG")
        
        # ZIP 생성 (메모리)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for idx, img in enumerate(processed_pil_images):
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format="PNG")
                zf.writestr(f"frame_{idx:03d}.png", img_byte_arr.getvalue())

        # 탭 1: GIF 미리보기
        with tab1:
            st.image(gif_buffer.getvalue(), caption="투명 배경 적용됨", use_container_width=True)
            st.caption("💡 배경이 검게 보이면 다크모드 때문일 수 있습니다. (실제로는 투명함)")

        # 탭 2: 다운로드
        with tab2:
            st.subheader("스프라이트 시트")
            st.image(sprite_sheet, use_container_width=True)
            
            # 버튼들을 꽉 차게 배치
            st.download_button(
                label="📄 스프라이트 시트(.png) 저장",
                data=sheet_buffer.getvalue(),
                file_name="sprite_sheet.png",
                mime="image/png",
                use_container_width=True
            )
            
            st.markdown("---")
            
            st.download_button(
                label="📦 낱개 프레임(.zip) 저장",
                data=zip_buffer.getvalue(),
                file_name="frames.zip",
                mime="application/zip",
                use_container_width=True
            )

    cap.release()
    tfile.close()
    os.unlink(tfile.name)