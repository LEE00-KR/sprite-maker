import streamlit as st
import cv2
import numpy as np
import tempfile
import os
import zipfile
from PIL import Image, ImageDraw
import io
import requests
import base64
from dotenv import load_dotenv

# .env 파일 로드 (로컬 개발용)
load_dotenv()

# Replicate API 토큰 (Streamlit Cloud secrets 우선, 없으면 .env)
def get_api_token():
    """Streamlit Cloud의 st.secrets 또는 .env에서 API 토큰 로드"""
    # Streamlit Cloud secrets 확인
    try:
        if "REPLICATE_API_TOKEN" in st.secrets:
            return st.secrets["REPLICATE_API_TOKEN"]
    except Exception:
        pass
    # 로컬 .env 파일 확인
    return os.getenv("REPLICATE_API_TOKEN", "")

REPLICATE_API_TOKEN = get_api_token()

# Replicate import (토큰이 있을 때만)
try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False

# --- 배경 제거 함수 ---
def remove_background(image, target_color, tolerance, edge_smoothing=0):
    """배경색을 제거하고 투명하게 만듦"""
    if len(image.shape) == 3 and image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)

    lower_bound = np.array([max(c - tolerance, 0) for c in target_color])
    upper_bound = np.array([min(c + tolerance, 255) for c in target_color])
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
    mask = cv2.inRange(rgb_image, lower_bound, upper_bound)
    mask_inv = cv2.bitwise_not(mask)

    if edge_smoothing > 0:
        blur_size = edge_smoothing * 2 + 1
        mask_inv = cv2.GaussianBlur(mask_inv, (blur_size, blur_size), 0)
        kernel = np.ones((3, 3), np.uint8)
        mask_inv = cv2.morphologyEx(mask_inv, cv2.MORPH_CLOSE, kernel)

    image[:, :, 3] = mask_inv
    return image

# --- 로고 영역 제거 ---
def remove_logo_area(image, regions):
    """지정된 영역을 투명하게 만듦"""
    if len(image.shape) == 3 and image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    for region in regions:
        x, y, w, h = int(region['x']), int(region['y']), int(region['width']), int(region['height'])
        x, y = max(0, x), max(0, y)
        w = min(w, image.shape[1] - x)
        h = min(h, image.shape[0] - y)
        if w > 0 and h > 0:
            image[y:y+h, x:x+w, 3] = 0
    return image

# --- 이미지 리사이즈 ---
def resize_image(pil_img, target_width, target_height):
    if target_width > 0 and target_height > 0:
        return pil_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    return pil_img

# --- 스프라이트 시트 생성 ---
def create_sprite_sheet(images, columns=0):
    if not images:
        return None
    width, height = images[0].size
    total_images = len(images)

    if columns <= 0:
        total_width = width * total_images
        sheet = Image.new("RGBA", (total_width, height))
        for idx, img in enumerate(images):
            sheet.paste(img, (idx * width, 0))
    else:
        rows = (total_images + columns - 1) // columns
        sheet = Image.new("RGBA", (width * columns, height * rows))
        for idx, img in enumerate(images):
            sheet.paste(img, ((idx % columns) * width, (idx // columns) * height))
    return sheet

# --- 단일 프레임 처리 (미리보기용) ---
def process_single_frame(frame_rgb, bg_color_rgb, tolerance, edge_smoothing, logo_regions=None):
    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

    if logo_regions:
        frame_bgra = remove_logo_area(frame_bgr.copy(), logo_regions)
        rgb_image = cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2RGB)
        lower_bound = np.array([max(c - tolerance, 0) for c in bg_color_rgb])
        upper_bound = np.array([min(c + tolerance, 255) for c in bg_color_rgb])
        mask = cv2.inRange(rgb_image, lower_bound, upper_bound)
        mask_inv = cv2.bitwise_not(mask)
        if edge_smoothing > 0:
            blur_size = edge_smoothing * 2 + 1
            mask_inv = cv2.GaussianBlur(mask_inv, (blur_size, blur_size), 0)
            kernel = np.ones((3, 3), np.uint8)
            mask_inv = cv2.morphologyEx(mask_inv, cv2.MORPH_CLOSE, kernel)
        frame_bgra[:, :, 3] = cv2.bitwise_and(frame_bgra[:, :, 3], mask_inv)
        processed_cv = frame_bgra
    else:
        processed_cv = remove_background(frame_bgr, bg_color_rgb, tolerance, edge_smoothing)

    return Image.fromarray(cv2.cvtColor(processed_cv, cv2.COLOR_BGRA2RGBA))

# --- AI 비디오 생성 ---
def generate_video_from_image(image_file, api_token, prompt="", video_length="25_frames_with_svd_xt", motion_bucket_id=127, fps=6):
    """Replicate API로 이미지에서 비디오 생성"""
    os.environ["REPLICATE_API_TOKEN"] = api_token

    image_bytes = image_file.getvalue()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    image_file.seek(0)
    header = image_file.read(8)
    image_file.seek(0)

    mime_type = "image/png" if header[:8] == b'\x89PNG\r\n\x1a\n' else "image/jpeg"
    data_uri = f"data:{mime_type};base64,{base64_image}"

    # Stable Video Diffusion 사용
    output = replicate.run(
        "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd3af8d253968904295257f682fd7a95f9c",
        input={
            "input_image": data_uri,
            "video_length": video_length,
            "motion_bucket_id": motion_bucket_id,
            "fps": fps
        }
    )

    return output

# --- 비디오 처리 파이프라인 ---
def process_video_to_sprites(video_path, bg_color_rgb, tolerance, edge_smoothing,
                              frame_interval, max_frames, use_custom_size,
                              output_width, output_height, logo_regions=None):
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    processed_pil_images = []

    frame_idx = 0
    extracted_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0 and extracted_count < max_frames:
            if logo_regions:
                frame = remove_logo_area(frame, logo_regions)
                processed_cv = frame.copy()
                rgb_image = cv2.cvtColor(processed_cv, cv2.COLOR_BGRA2RGB)
                lower_bound = np.array([max(c - tolerance, 0) for c in bg_color_rgb])
                upper_bound = np.array([min(c + tolerance, 255) for c in bg_color_rgb])
                mask = cv2.inRange(rgb_image, lower_bound, upper_bound)
                mask_inv = cv2.bitwise_not(mask)
                if edge_smoothing > 0:
                    blur_size = edge_smoothing * 2 + 1
                    mask_inv = cv2.GaussianBlur(mask_inv, (blur_size, blur_size), 0)
                    kernel = np.ones((3, 3), np.uint8)
                    mask_inv = cv2.morphologyEx(mask_inv, cv2.MORPH_CLOSE, kernel)
                processed_cv[:, :, 3] = cv2.bitwise_and(processed_cv[:, :, 3], mask_inv)
            else:
                processed_cv = remove_background(frame, bg_color_rgb, tolerance, edge_smoothing)

            pil_img = Image.fromarray(cv2.cvtColor(processed_cv, cv2.COLOR_BGRA2RGBA))

            if use_custom_size and output_width > 0 and output_height > 0:
                pil_img = resize_image(pil_img, output_width, output_height)

            processed_pil_images.append(pil_img)
            extracted_count += 1

        frame_idx += 1
        if extracted_count >= max_frames:
            break

    cap.release()
    return processed_pil_images, total_frames

# --- 체크무늬 배경 생성 ---
def create_checker_background(width, height, checker_size=10):
    checker = Image.new('RGB', (width, height))
    for i in range(0, width, checker_size):
        for j in range(0, height, checker_size):
            color = (200, 200, 200) if (i // checker_size + j // checker_size) % 2 == 0 else (255, 255, 255)
            for x in range(i, min(i + checker_size, width)):
                for y in range(j, min(j + checker_size, height)):
                    checker.putpixel((x, y), color)
    return checker

# ===== UI 설정 =====
st.set_page_config(page_title="Sprite Maker + AI", layout="wide")
st.header("🦖 스프라이트 생성기")

# ===== 세션 상태 초기화 =====
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'uploaded_image' not in st.session_state:
    st.session_state.uploaded_image = None
if 'generated_video_path' not in st.session_state:
    st.session_state.generated_video_path = None
if 'video_frames' not in st.session_state:
    st.session_state.video_frames = None
if 'processed_images' not in st.session_state:
    st.session_state.processed_images = []
if 'logo_regions' not in st.session_state:
    st.session_state.logo_regions = []

# ===== 사이드바: 모드 선택 =====
with st.sidebar:
    st.subheader("📌 작업 모드")
    app_mode = st.radio(
        "모드 선택",
        ["📹 비디오 업로드", "🤖 AI 생성 (이미지→비디오)"],
        key="app_mode"
    )

    # API 토큰 상태 표시
    if "AI 생성" in app_mode:
        st.markdown("---")
        st.subheader("🔑 API 상태")
        if REPLICATE_API_TOKEN:
            st.success("✅ API 토큰 로드됨")
        else:
            st.error("❌ API 토큰 없음")
            st.caption("Streamlit Cloud: Secrets에 설정")
            st.caption("로컬: `.env` 파일에 설정")

    st.markdown("---")
    st.caption("📋 현재 단계")
    if "AI 생성" in app_mode:
        steps = ["1️⃣ 이미지 업로드", "2️⃣ AI 비디오 생성", "3️⃣ 배경 설정", "4️⃣ 결과물"]
    else:
        steps = ["1️⃣ 비디오 업로드", "2️⃣ 배경 설정", "3️⃣ 결과물"]

    for i, step in enumerate(steps, 1):
        if i < st.session_state.current_step:
            st.write(f"✅ {step}")
        elif i == st.session_state.current_step:
            st.write(f"👉 **{step}**")
        else:
            st.write(f"⬜ {step}")

# ===== AI 생성 모드 =====
if "AI 생성" in app_mode:

    # ========== STEP 1: 이미지 업로드 ==========
    st.subheader("📤 Step 1: 이미지 업로드")

    uploaded_image = st.file_uploader(
        "이미지 파일 (PNG/JPG)",
        type=["png", "jpg", "jpeg"],
        key="ai_image_uploader"
    )

    if uploaded_image:
        st.session_state.uploaded_image = uploaded_image
        image = Image.open(uploaded_image)

        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(image, caption=f"업로드된 이미지 ({image.width}x{image.height})", width="stretch")

        with col2:
            st.success("✅ 이미지 업로드 완료!")
            st.caption("다음 단계에서 AI가 이 이미지를 움직이는 비디오로 변환합니다.")

        if st.session_state.current_step < 2:
            st.session_state.current_step = 2

    # ========== STEP 2: AI 비디오 생성 ==========
    if st.session_state.current_step >= 2 and st.session_state.uploaded_image:
        st.markdown("---")
        st.subheader("🤖 Step 2: AI 비디오 생성")

        if not REPLICATE_API_TOKEN:
            st.error("❌ Replicate API 토큰이 설정되지 않았습니다.")
            st.markdown("""
**Streamlit Cloud 배포:**
1. 앱 대시보드 → Settings → Secrets
2. 아래 내용 추가:
```toml
REPLICATE_API_TOKEN = "your_token_here"
```

**로컬 실행:**
- `.env` 파일에 `REPLICATE_API_TOKEN=your_token` 추가
            """)
            st.stop()

        # AI 생성 옵션
        with st.expander("🎬 AI 생성 옵션", expanded=True):
            ai_prompt = st.text_area(
                "프롬프트 (선택사항)",
                placeholder="예: gentle swaying motion, breathing animation, subtle movement...",
                help="원하는 움직임을 설명하세요. (현재 SVD 모델은 프롬프트 영향이 제한적)"
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                video_length = st.selectbox(
                    "비디오 길이",
                    ["14_frames_with_svd", "25_frames_with_svd_xt"],
                    index=1
                )
            with col2:
                motion_bucket_id = st.slider("모션 강도", 1, 255, 127, help="높을수록 움직임 큼")
            with col3:
                ai_fps = st.slider("FPS", 1, 30, 6)

        # 이미 생성된 비디오가 있는지 확인
        if st.session_state.generated_video_path and os.path.exists(st.session_state.generated_video_path):
            st.success("✅ AI 비디오 생성 완료!")
            st.video(st.session_state.generated_video_path)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 다시 생성하기", width="stretch"):
                    st.session_state.generated_video_path = None
                    st.session_state.current_step = 2
                    st.rerun()
            with col2:
                if st.button("➡️ 다음 단계로", type="primary", width="stretch"):
                    st.session_state.current_step = 3
                    st.rerun()
        else:
            # AI 생성 버튼
            if st.button("🚀 AI 비디오 생성 시작", type="primary", width="stretch"):
                with st.status("🤖 AI 비디오 생성 중...", expanded=True) as status:
                    st.write("⏳ Stable Video Diffusion 실행 중...")
                    st.write("   약 2~5분 소요됩니다.")

                    try:
                        st.session_state.uploaded_image.seek(0)
                        video_url = generate_video_from_image(
                            st.session_state.uploaded_image,
                            REPLICATE_API_TOKEN,
                            prompt=ai_prompt,
                            video_length=video_length,
                            motion_bucket_id=motion_bucket_id,
                            fps=ai_fps
                        )

                        st.write("✅ 생성 완료! 다운로드 중...")

                        response = requests.get(video_url)
                        video_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                        video_temp.write(response.content)
                        video_temp.close()

                        st.session_state.generated_video_path = video_temp.name
                        status.update(label="✅ AI 비디오 생성 완료!", state="complete")
                        st.rerun()

                    except Exception as e:
                        status.update(label="❌ 생성 실패", state="error")
                        st.error(f"오류: {str(e)}")

    # ========== STEP 3: 배경 제거 설정 ==========
    if st.session_state.current_step >= 3 and st.session_state.generated_video_path:
        st.markdown("---")
        st.subheader("⚙️ Step 3: 배경 제거 설정")

        # 비디오에서 첫 프레임 추출
        cap = cv2.VideoCapture(st.session_state.generated_video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        ret, first_frame = cap.read()
        cap.release()

        if ret:
            first_frame_rgb = cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)

            st.info(f"📹 비디오 정보: {video_width}x{video_height} | {total_frames}프레임")

            # 배경 제거 옵션
            with st.expander("🎨 배경 제거 옵션", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    bg_color_hex = st.color_picker("제거할 배경색", "#000000")
                with col2:
                    tolerance = st.slider("민감도", 0, 150, 100)
                with col3:
                    edge_smoothing = st.slider("경계선 부드럽게", 0, 10, 3)

            # 출력 설정
            with st.expander("📐 출력 설정", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    use_custom_size = st.checkbox("크기 직접 지정")
                    if use_custom_size:
                        output_width = st.number_input("너비", 1, 4096, video_width)
                        output_height = st.number_input("높이", 1, 4096, video_height)
                    else:
                        output_width, output_height = video_width, video_height

                with col2:
                    frame_interval = st.number_input("프레임 추출 간격", 1, 30, 1)
                    max_frames = st.number_input("최대 프레임", 1, total_frames, min(total_frames, 100))

                gif_speed = st.slider("GIF 속도 (ms/프레임)", 10, 500, 100)

            # 미리보기
            st.markdown("### 👁️ 미리보기")
            bg_color_rgb = tuple(int(bg_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**원본**")
                st.image(first_frame_rgb, width="stretch")
            with col2:
                st.markdown("**배경 제거 적용**")
                preview = process_single_frame(first_frame_rgb, bg_color_rgb, tolerance, edge_smoothing)
                checker = create_checker_background(preview.width, preview.height)
                checker.paste(preview, (0, 0), preview)
                st.image(checker, width="stretch")
                st.caption("🔲 체크무늬 = 투명 영역")

            # 스프라이트 변환 버튼
            if st.button("✨ 스프라이트 시트 생성", type="primary", width="stretch"):
                with st.spinner("변환 중..."):
                    processed_images, _ = process_video_to_sprites(
                        st.session_state.generated_video_path,
                        bg_color_rgb, tolerance, edge_smoothing,
                        frame_interval, max_frames, use_custom_size,
                        output_width, output_height, st.session_state.logo_regions
                    )
                    st.session_state.processed_images = processed_images
                    st.session_state.gif_speed = gif_speed
                    st.session_state.current_step = 4
                    st.rerun()

# ===== 비디오 업로드 모드 =====
else:
    # ========== STEP 1: 비디오 업로드 ==========
    st.subheader("📤 Step 1: 비디오 업로드")

    uploaded_video = st.file_uploader(
        "비디오 파일 (MP4/MOV/AVI)",
        type=["mp4", "mov", "avi"],
        key="video_uploader"
    )

    if uploaded_video:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(uploaded_video.read())
        tfile.close()
        st.session_state.generated_video_path = tfile.name

        cap = cv2.VideoCapture(tfile.name)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        ret, first_frame = cap.read()
        cap.release()

        st.info(f"📹 비디오 정보: {video_width}x{video_height} | {total_frames}프레임 | {video_fps:.1f}fps")

        if ret:
            first_frame_rgb = cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)
            st.image(first_frame_rgb, caption="첫 프레임", width="stretch")

        st.session_state.current_step = 2

    # ========== STEP 2: 배경 설정 ==========
    if st.session_state.current_step >= 2 and st.session_state.generated_video_path:
        st.markdown("---")
        st.subheader("⚙️ Step 2: 배경 제거 설정")

        cap = cv2.VideoCapture(st.session_state.generated_video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        ret, first_frame = cap.read()
        cap.release()

        if ret:
            first_frame_rgb = cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)

            with st.expander("🎨 배경 제거 옵션", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    bg_color_hex = st.color_picker("제거할 배경색", "#000000", key="video_bg")
                with col2:
                    tolerance = st.slider("민감도", 0, 150, 100, key="video_tol")
                with col3:
                    edge_smoothing = st.slider("경계선 부드럽게", 0, 10, 3, key="video_edge")

            with st.expander("📐 출력 설정", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    use_custom_size = st.checkbox("크기 직접 지정", key="video_custom")
                    if use_custom_size:
                        output_width = st.number_input("너비", 1, 4096, video_width, key="video_w")
                        output_height = st.number_input("높이", 1, 4096, video_height, key="video_h")
                    else:
                        output_width, output_height = video_width, video_height
                with col2:
                    frame_interval = st.number_input("추출 간격", 1, 30, 1, key="video_int")
                    max_frames = st.number_input("최대 프레임", 1, total_frames, min(total_frames, 100), key="video_max")

                gif_speed = st.slider("GIF 속도", 10, 500, 100, key="video_gif")

            # 미리보기
            st.markdown("### 👁️ 미리보기")
            bg_color_rgb = tuple(int(bg_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**원본**")
                st.image(first_frame_rgb, width="stretch")
            with col2:
                st.markdown("**배경 제거 적용**")
                preview = process_single_frame(first_frame_rgb, bg_color_rgb, tolerance, edge_smoothing)
                checker = create_checker_background(preview.width, preview.height)
                checker.paste(preview, (0, 0), preview)
                st.image(checker, width="stretch")

            if st.button("✨ 스프라이트 시트 생성", type="primary", width="stretch", key="video_convert"):
                with st.spinner("변환 중..."):
                    processed_images, _ = process_video_to_sprites(
                        st.session_state.generated_video_path,
                        bg_color_rgb, tolerance, edge_smoothing,
                        frame_interval, max_frames, use_custom_size,
                        output_width, output_height, []
                    )
                    st.session_state.processed_images = processed_images
                    st.session_state.gif_speed = gif_speed
                    st.session_state.current_step = 3
                    st.rerun()

# ===== 결과물 표시 =====
if st.session_state.processed_images:
    st.markdown("---")
    st.header("📦 결과물")

    processed_pil_images = st.session_state.processed_images
    current_gif_speed = st.session_state.get('gif_speed', 100)

    tab1, tab2, tab3 = st.tabs(["🎬 GIF", "📄 스프라이트 시트", "🖼️ 프레임 선택"])

    with tab1:
        gif_buffer = io.BytesIO()
        processed_pil_images[0].save(
            gif_buffer, format="GIF", save_all=True,
            append_images=processed_pil_images[1:],
            duration=current_gif_speed, loop=0, disposal=2, transparency=0
        )
        st.image(gif_buffer.getvalue(), caption="투명 배경 GIF")
        st.download_button("🎬 GIF 다운로드", gif_buffer.getvalue(), "animation.gif", "image/gif", width="stretch")

    with tab2:
        sheet_cols = st.number_input("열 수 (0=가로 한 줄)", 0, len(processed_pil_images), 0)
        sprite_sheet = create_sprite_sheet(processed_pil_images, sheet_cols)
        sheet_buffer = io.BytesIO()
        sprite_sheet.save(sheet_buffer, format="PNG")
        st.image(sprite_sheet, caption=f"스프라이트 시트 ({sprite_sheet.width}x{sprite_sheet.height})")

        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📄 PNG 저장", sheet_buffer.getvalue(), "sprite_sheet.png", "image/png", width="stretch")
        with col2:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for idx, img in enumerate(processed_pil_images):
                    img_arr = io.BytesIO()
                    img.save(img_arr, format="PNG")
                    zf.writestr(f"frame_{idx:03d}.png", img_arr.getvalue())
            st.download_button("📦 ZIP 저장", zip_buffer.getvalue(), "frames.zip", "application/zip", width="stretch")

    with tab3:
        if 'selected_frames' not in st.session_state:
            st.session_state.selected_frames = list(range(len(processed_pil_images)))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 전체 선택", width="stretch"):
                st.session_state.selected_frames = list(range(len(processed_pil_images)))
                st.rerun()
        with col2:
            if st.button("❌ 전체 해제", width="stretch"):
                st.session_state.selected_frames = []
                st.rerun()

        cols_per_row = 6
        for row_start in range(0, len(processed_pil_images), cols_per_row):
            cols = st.columns(cols_per_row)
            for col_idx, img_idx in enumerate(range(row_start, min(row_start + cols_per_row, len(processed_pil_images)))):
                with cols[col_idx]:
                    is_sel = img_idx in st.session_state.selected_frames
                    if st.checkbox(f"#{img_idx+1}", value=is_sel, key=f"sel_{img_idx}"):
                        if img_idx not in st.session_state.selected_frames:
                            st.session_state.selected_frames.append(img_idx)
                    else:
                        if img_idx in st.session_state.selected_frames:
                            st.session_state.selected_frames.remove(img_idx)
                    thumb = processed_pil_images[img_idx].copy()
                    thumb.thumbnail((80, 80))
                    st.image(thumb)

        if st.session_state.selected_frames:
            st.info(f"선택: {len(st.session_state.selected_frames)}개")
            selected_imgs = [processed_pil_images[i] for i in sorted(st.session_state.selected_frames)]
            custom_cols = st.number_input("열 수", 0, len(selected_imgs), 0, key="custom_cols")
            custom_sheet = create_sprite_sheet(selected_imgs, custom_cols)
            custom_buf = io.BytesIO()
            custom_sheet.save(custom_buf, format="PNG")
            st.image(custom_sheet)
            st.download_button("📄 선택 프레임 저장", custom_buf.getvalue(), "custom_sheet.png", "image/png", width="stretch")

    # 처음부터 다시하기
    st.markdown("---")
    if st.button("🔄 처음부터 다시하기", width="stretch"):
        st.session_state.current_step = 1
        st.session_state.uploaded_image = None
        st.session_state.generated_video_path = None
        st.session_state.processed_images = []
        st.session_state.selected_frames = []
        st.rerun()
