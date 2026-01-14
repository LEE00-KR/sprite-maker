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
from streamlit_image_coordinates import streamlit_image_coordinates

# ============================================
# API 토큰 설정 (가장 먼저 실행되어야 함)
# ============================================

# 1. 로컬 .env 파일 로드
load_dotenv()

# 2. Streamlit Cloud secrets에서 토큰 가져와서 os.environ에 강제 주입
try:
    if "REPLICATE_API_TOKEN" in st.secrets:
        os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
except FileNotFoundError:
    # secrets.toml 파일이 없는 경우 (로컬 환경)
    pass

# 3. 최종 토큰 값 확인
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")

# Replicate import
try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False

# ============================================
# 단계 정의
# ============================================
STEPS = {
    1: "소스 입력",
    2: "영상 확인",
    3: "배경 제거",
    4: "프레임 선택",
    5: "다운로드"
}

# ============================================
# Apple 스타일 다크모드 CSS
# ============================================
def apply_dark_theme_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        .stApp {
            background-color: #000000;
            font-family: 'Inter', -apple-system, sans-serif;
        }

        h1, h2, h3 {
            color: #F5F5F7 !important;
            font-weight: 700;
        }

        .stButton > button {
            border-radius: 12px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        .stButton > button:hover {
            transform: scale(1.02);
        }

        /* Primary 버튼 */
        div[data-testid="stButton"] button[kind="primary"] {
            background-color: #0A84FF;
        }

        /* 이미지 둥글게 */
        img {
            border-radius: 12px;
        }

        /* 슬라이더 컬러 */
        .stSlider > div > div > div {
            background-color: #0A84FF;
        }

        /* Step Indicator 스타일 */
        .step-indicator {
            display: flex;
            justify-content: space-between;
            padding: 20px 0;
            margin-bottom: 20px;
            border-bottom: 1px solid #333;
        }
        .step-item {
            text-align: center;
            flex: 1;
        }
        .step-current {
            color: #0A84FF;
            font-weight: 700;
        }
        .step-completed {
            color: #30D158;
        }
        .step-pending {
            color: #666;
        }

        /* 색상 박스 스타일 */
        .color-box {
            width: 60px;
            height: 60px;
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            font-size: 24px;
            color: #fff;
            text-shadow: 0 0 3px #000;
            transition: transform 0.2s;
        }
        .color-box:hover {
            transform: scale(1.05);
        }
        .color-box-selected {
            border: 3px solid #30D158 !important;
        }

        /* 프레임 그리드 스타일 */
        .frame-selected {
            border: 3px solid #30D158;
            border-radius: 12px;
            padding: 4px;
        }
        .frame-unselected {
            border: 2px solid #333;
            border-radius: 12px;
            padding: 4px;
        }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 세션 상태 통합 관리
# ============================================
def init_session():
    """세션 상태 초기화 - 앱 시작 시 한 번만 실행"""
    defaults = {
        'step': 1,
        'mode': None,  # 'ai' or 'video'
        'video_path': None,
        'video_frames': [],  # numpy array list (RGB)
        'bg_colors': [],  # 제거할 배경색 목록 (hex)
        'tolerance': 60,
        'edge_smoothing': 1.0,
        'use_hsv': True,
        'processed_frames': [],  # 배경 제거된 PIL Image list
        'selected_frame_indices': [],  # 선택된 프레임 인덱스
        'gif_speed': 100,
        'uploaded_image': None,
        'use_custom_size': False,
        'output_width': 512,
        'output_height': 512,
        'frame_interval': 1,
        'max_frames': 100,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_to_step(step_num):
    """특정 단계로 리셋"""
    st.session_state.step = step_num
    if step_num <= 1:
        st.session_state.video_path = None
        st.session_state.video_frames = []
        st.session_state.uploaded_image = None
    if step_num <= 2:
        st.session_state.bg_colors = []
    if step_num <= 3:
        st.session_state.processed_frames = []
    if step_num <= 4:
        st.session_state.selected_frame_indices = []

# ============================================
# Step Indicator UI
# ============================================
def show_step_indicator(current_step):
    """상단에 진행 단계 표시"""
    cols = st.columns(5)
    for i, (num, name) in enumerate(STEPS.items()):
        with cols[i]:
            if current_step == num:
                st.markdown(f"**🔵 {num}. {name}**")
            elif current_step > num:
                st.markdown(f"✅ {num}. {name}")
            else:
                st.markdown(f"⚪ {num}. {name}")
    st.markdown("---")

# ============================================
# 유틸리티 함수들
# ============================================

def hex_to_rgb(hex_color):
    """HEX 색상을 RGB 튜플로 변환"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def remove_background_multi(image, target_colors, tolerance, edge_smoothing=0.0, use_hsv=True):
    """
    여러 배경색을 제거하고 투명하게 만듦 (그라데이션 대응)
    """
    if len(image.shape) == 3 and image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)

    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
    combined_mask = np.zeros(rgb_image.shape[:2], dtype=np.uint8)

    for target_color in target_colors:
        # RGB 기반 마스크
        lower_bound = np.array([max(c - tolerance, 0) for c in target_color])
        upper_bound = np.array([min(c + tolerance, 255) for c in target_color])
        rgb_mask = cv2.inRange(rgb_image, lower_bound, upper_bound)

        if use_hsv:
            # HSV 기반 마스크 (그라데이션 색상 대응)
            hsv_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2HSV)
            target_hsv = cv2.cvtColor(np.uint8([[target_color]]), cv2.COLOR_RGB2HSV)[0][0]

            h_tol = max(15, tolerance // 5)
            s_tol = tolerance
            v_tol = tolerance

            lower_hsv = np.array([max(target_hsv[0] - h_tol, 0),
                                  max(target_hsv[1] - s_tol, 0),
                                  max(target_hsv[2] - v_tol, 0)])
            upper_hsv = np.array([min(target_hsv[0] + h_tol, 179),
                                  min(target_hsv[1] + s_tol, 255),
                                  min(target_hsv[2] + v_tol, 255)])

            hsv_mask = cv2.inRange(hsv_image, lower_hsv, upper_hsv)
            color_mask = cv2.bitwise_or(rgb_mask, hsv_mask)
        else:
            color_mask = rgb_mask

        combined_mask = cv2.bitwise_or(combined_mask, color_mask)

    mask_inv = cv2.bitwise_not(combined_mask)

    if edge_smoothing > 0:
        blur_size = int(edge_smoothing * 2) + 1
        if blur_size % 2 == 0:
            blur_size += 1

        mask_smooth = cv2.GaussianBlur(mask_inv, (blur_size, blur_size), 0)

        kernel_size = max(3, int(edge_smoothing))
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        mask_smooth = cv2.morphologyEx(mask_smooth, cv2.MORPH_CLOSE, kernel)

        mask_inv = mask_smooth

    image[:, :, 3] = mask_inv
    image = fill_transparent_with_nearby_color(image)

    return image

def fill_transparent_with_nearby_color(image):
    """투명/반투명 영역의 RGB 값을 인접한 불투명 픽셀 색상으로 채움"""
    alpha = image[:, :, 3]
    rgb = image[:, :, :3].copy()

    opaque_mask = (alpha > 200).astype(np.uint8)
    transparent_mask = (alpha <= 200).astype(np.uint8)

    if np.sum(transparent_mask) == 0:
        return image

    kernel = np.ones((5, 5), np.uint8)
    for c in range(3):
        channel = rgb[:, :, c].astype(np.float32)
        masked_channel = channel * opaque_mask
        dilated = cv2.dilate(masked_channel, kernel, iterations=3)
        rgb[:, :, c] = np.where(transparent_mask > 0, dilated, channel).astype(np.uint8)

    image[:, :, :3] = rgb
    return image

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

def resize_image(pil_img, target_width, target_height):
    if target_width > 0 and target_height > 0:
        return pil_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    return pil_img

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

def process_single_frame(frame_rgb, bg_colors_rgb, tolerance, edge_smoothing, logo_regions=None, use_hsv=True):
    """단일 프레임의 배경 제거 처리 (미리보기용)"""
    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

    if isinstance(bg_colors_rgb, tuple) and len(bg_colors_rgb) == 3 and isinstance(bg_colors_rgb[0], int):
        bg_colors_rgb = [bg_colors_rgb]

    if logo_regions:
        frame_bgra = remove_logo_area(frame_bgr.copy(), logo_regions)
        processed_cv = remove_background_multi(frame_bgra, bg_colors_rgb, tolerance, edge_smoothing, use_hsv)
    else:
        processed_cv = remove_background_multi(frame_bgr, bg_colors_rgb, tolerance, edge_smoothing, use_hsv)

    return Image.fromarray(cv2.cvtColor(processed_cv, cv2.COLOR_BGRA2RGBA))

def generate_video_from_image(image_file, api_token, prompt="", video_length="25_frames_with_svd_xt", motion_bucket_id=60, fps=30):
    """Replicate API로 이미지에서 비디오 생성"""
    os.environ["REPLICATE_API_TOKEN"] = api_token

    image_bytes = image_file.getvalue()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    image_file.seek(0)
    header = image_file.read(8)
    image_file.seek(0)

    mime_type = "image/png" if header[:8] == b'\x89PNG\r\n\x1a\n' else "image/jpeg"
    data_uri = f"data:{mime_type};base64,{base64_image}"

    output = replicate.run(
        "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
        input={
            "input_image": data_uri,
            "video_length": video_length,
            "motion_bucket_id": motion_bucket_id,
            "fps": fps
        }
    )

    return output

def extract_frames_from_video(video_path):
    """비디오에서 모든 프레임을 추출하여 RGB numpy array 리스트로 반환"""
    cap = cv2.VideoCapture(video_path)
    frames = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame_rgb)

    cap.release()
    return frames

def process_all_frames():
    """모든 프레임에 배경 제거 적용"""
    frames = st.session_state.video_frames
    bg_colors_rgb = [hex_to_rgb(c) for c in st.session_state.bg_colors]

    if not bg_colors_rgb:
        bg_colors_rgb = [(255, 255, 255)]

    processed = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, frame_rgb in enumerate(frames):
        status_text.text(f"프레임 처리 중... {i+1}/{len(frames)}")

        pil_img = process_single_frame(
            frame_rgb, bg_colors_rgb,
            st.session_state.tolerance,
            st.session_state.edge_smoothing,
            use_hsv=st.session_state.use_hsv
        )

        if st.session_state.use_custom_size:
            pil_img = resize_image(pil_img, st.session_state.output_width, st.session_state.output_height)

        processed.append(pil_img)
        progress_bar.progress((i + 1) / len(frames))

    status_text.empty()
    progress_bar.empty()

    st.session_state.processed_frames = processed
    st.session_state.selected_frame_indices = list(range(len(processed)))

def get_color_at_position(image_rgb, x, y):
    """이미지의 특정 좌표에서 RGB 색상 추출"""
    if 0 <= x < image_rgb.shape[1] and 0 <= y < image_rgb.shape[0]:
        r, g, b = image_rgb[int(y), int(x)]
        return f"#{r:02x}{g:02x}{b:02x}"
    return "#000000"

def extract_dominant_colors(image_rgb, n_colors=8):
    """이미지 가장자리에서 주요 배경색 후보 추출"""
    from collections import Counter
    h, w = image_rgb.shape[:2]
    edge_size = min(10, h // 4, w // 4)
    edges = []
    edges.extend(image_rgb[:edge_size, :].reshape(-1, 3).tolist())
    edges.extend(image_rgb[-edge_size:, :].reshape(-1, 3).tolist())
    edges.extend(image_rgb[:, :edge_size].reshape(-1, 3).tolist())
    edges.extend(image_rgb[:, -edge_size:].reshape(-1, 3).tolist())
    color_counts = Counter([tuple(c) for c in edges])
    most_common = color_counts.most_common(n_colors)
    return [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in most_common]

def create_checker_background(width, height, checker_size=15):
    checker = Image.new('RGB', (width, height))
    for i in range(0, width, checker_size):
        for j in range(0, height, checker_size):
            color = (200, 200, 200) if (i // checker_size + j // checker_size) % 2 == 0 else (255, 255, 255)
            for x in range(i, min(i + checker_size, width)):
                for y in range(j, min(j + checker_size, height)):
                    checker.putpixel((x, y), color)
    return checker

def create_clean_gif_frames(images):
    """RGBA 이미지를 GIF용 팔레트 이미지로 변환"""
    converted_frames = []

    for frame in images:
        if frame.mode == 'RGBA':
            r, g, b, a = frame.split()
            alpha = np.array(a)

            alpha_threshold = 128
            alpha_binary = np.where(alpha >= alpha_threshold, 255, 0).astype(np.uint8)

            kernel = np.ones((2, 2), np.uint8)
            alpha_eroded = cv2.erode(alpha_binary, kernel, iterations=1)

            rgb_array = np.array(frame.convert('RGB'))
            mask_opaque = alpha_eroded > 0

            for c in range(3):
                channel = rgb_array[:, :, c].astype(np.float32)
                dilated = cv2.dilate(channel, kernel, iterations=2)
                rgb_array[:, :, c] = np.where(mask_opaque, channel, dilated).astype(np.uint8)

            clean_frame = Image.fromarray(rgb_array, 'RGB')
            clean_alpha = Image.fromarray(alpha_eroded, 'L')

            trans_color = (0, 255, 254)
            background = Image.new('RGB', frame.size, trans_color)
            background.paste(clean_frame, (0, 0), clean_alpha)

            p_frame = background.convert('P', palette=Image.ADAPTIVE, colors=255)

            palette = p_frame.getpalette()
            trans_index = 0
            for i in range(256):
                if palette[i*3:i*3+3] == list(trans_color):
                    trans_index = i
                    break

            converted_frames.append((p_frame, trans_index))
        else:
            converted_frames.append((frame.convert('P', palette=Image.ADAPTIVE, colors=256), None))

    return converted_frames

# ============================================
# 공통 UI 함수들
# ============================================

def render_background_removal_ui(first_frame_rgb):
    """
    배경 제거 설정 UI - AI 모드/비디오 모드 모두 동일하게 사용
    레이아웃: 2열 구성 (왼쪽: 설정 패널, 오른쪽: 실시간 미리보기)
    """
    col_settings, col_preview = st.columns([1, 1.5])

    with col_settings:
        st.subheader("🎨 배경색 선택")

        # 1. 추천 색상 표시
        dominant_colors = extract_dominant_colors(first_frame_rgb, 8)
        st.caption("📌 추천 배경색 (클릭하여 추가/제거)")

        # 색상 박스 HTML 표시
        color_box_html = "<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:15px;'>"
        for i, color in enumerate(dominant_colors):
            is_selected = color in st.session_state.bg_colors
            border = "3px solid #30D158" if is_selected else "2px solid #555"
            check_mark = "✓" if is_selected else ""
            color_box_html += f"""
            <div style='width:60px;height:60px;background:{color};border:{border};border-radius:8px;
            display:flex;align-items:center;justify-content:center;box-shadow:0 2px 4px rgba(0,0,0,0.2);
            font-size:24px;color:#fff;text-shadow:0 0 3px #000;' title='{color}'>{check_mark}</div>
            """
        color_box_html += "</div>"
        st.markdown(color_box_html, unsafe_allow_html=True)

        # 버튼으로 색상 추가/제거
        color_cols = st.columns(4)
        for i, hex_color in enumerate(dominant_colors):
            with color_cols[i % 4]:
                is_selected = hex_color in st.session_state.bg_colors
                btn_label = "✓ 선택됨" if is_selected else "추가"
                if st.button(btn_label, key=f"color_{i}", use_container_width=True):
                    if is_selected:
                        st.session_state.bg_colors.remove(hex_color)
                    else:
                        st.session_state.bg_colors.append(hex_color)
                    st.rerun()

        st.markdown("---")

        # 2. 선택된 색상 목록
        st.caption(f"🎯 제거할 색상: {len(st.session_state.bg_colors)}개")
        if st.session_state.bg_colors:
            colors_html = "<div style='display:flex;flex-wrap:wrap;gap:10px;padding:15px;background:#1e1e1e;border-radius:8px;margin-bottom:10px;'>"
            for color in st.session_state.bg_colors:
                colors_html += f"""
                <div style='display:flex;flex-direction:column;align-items:center;'>
                    <div style='width:40px;height:40px;background:{color};border:2px solid #fff;border-radius:6px;'></div>
                    <div style='font-size:9px;color:#aaa;margin-top:4px;'>{color}</div>
                </div>
                """
            colors_html += "</div>"
            st.markdown(colors_html, unsafe_allow_html=True)

            # 개별 색상 제거 버튼
            remove_cols = st.columns(min(len(st.session_state.bg_colors), 6))
            for i, color in enumerate(st.session_state.bg_colors[:6]):
                with remove_cols[i]:
                    if st.button("✕", key=f"remove_{i}", use_container_width=True):
                        st.session_state.bg_colors.remove(color)
                        st.rerun()

            if st.button("🗑️ 모든 색상 초기화"):
                st.session_state.bg_colors = []
                st.rerun()
        else:
            st.info("💡 위에서 제거할 배경색을 선택하세요.")

        st.markdown("---")

        # 3. 커스텀 색상 추가
        st.caption("🎨 직접 색상 선택")
        col_pick, col_add = st.columns([3, 1])
        with col_pick:
            custom_color = st.color_picker("색상", "#ffffff", key="custom_picker")
        with col_add:
            st.write("")
            st.write("")
            if st.button("추가", key="add_custom"):
                if custom_color not in st.session_state.bg_colors:
                    st.session_state.bg_colors.append(custom_color)
                    st.rerun()

        st.markdown("---")

        # 4. 파라미터 슬라이더
        st.caption("⚙️ 제거 설정")
        st.session_state.tolerance = st.slider(
            "민감도 (색상 허용 범위)", 0, 150,
            st.session_state.tolerance,
            help="높을수록 비슷한 색상도 함께 제거"
        )
        st.session_state.edge_smoothing = st.slider(
            "경계선 부드럽게", 0.0, 5.0,
            st.session_state.edge_smoothing, step=0.5
        )
        st.session_state.use_hsv = st.checkbox(
            "🌈 HSV 매칭 (그라데이션 대응)",
            st.session_state.use_hsv,
            help="비슷한 색조의 그라데이션도 함께 제거"
        )

        st.markdown("---")

        # 5. 출력 설정
        st.caption("📐 출력 설정")
        st.session_state.use_custom_size = st.checkbox("크기 직접 지정", st.session_state.use_custom_size)
        if st.session_state.use_custom_size:
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.output_width = st.number_input("너비", 1, 4096, st.session_state.output_width)
            with col2:
                st.session_state.output_height = st.number_input("높이", 1, 4096, st.session_state.output_height)

    with col_preview:
        st.subheader("👁️ 실시간 미리보기")

        # 스포이드 기능
        st.caption("🔍 이미지 클릭으로 색상 추출")
        frame_pil = Image.fromarray(first_frame_rgb)
        display_width = min(500, frame_pil.width)
        scale = display_width / frame_pil.width
        display_height = int(frame_pil.height * scale)
        frame_display = frame_pil.resize((display_width, display_height), Image.Resampling.LANCZOS)

        coords = streamlit_image_coordinates(frame_display, key="eyedropper")

        if coords is not None:
            orig_x = int(coords["x"] / scale)
            orig_y = int(coords["y"] / scale)
            picked = get_color_at_position(first_frame_rgb, orig_x, orig_y)
            if picked not in st.session_state.bg_colors:
                st.session_state.bg_colors.append(picked)
                st.rerun()

        st.markdown("---")

        # 원본 vs 처리 결과 비교
        tab_orig, tab_proc = st.tabs(["📷 원본", "✨ 배경 제거"])

        with tab_orig:
            st.image(first_frame_rgb, use_container_width=True)

        with tab_proc:
            if st.session_state.bg_colors:
                colors_rgb = [hex_to_rgb(c) for c in st.session_state.bg_colors]
                preview = process_single_frame(
                    first_frame_rgb, colors_rgb,
                    st.session_state.tolerance,
                    st.session_state.edge_smoothing,
                    use_hsv=st.session_state.use_hsv
                )
                # 체크무늬 배경에 합성
                checker = create_checker_background(preview.width, preview.height, 15)
                checker.paste(preview, (0, 0), preview)
                st.image(checker, use_container_width=True)
                st.caption("🔲 체크무늬 = 투명 영역")
            else:
                st.warning("제거할 배경색을 선택해주세요")

def render_frame_selection_ui():
    """프레임 선택 화면 - 애니메이션 미리보기 포함"""
    frames = st.session_state.processed_frames

    if not frames:
        st.error("처리된 프레임이 없습니다")
        return

    # ===== 상단: 선택된 프레임 애니메이션 미리보기 =====
    st.subheader("🎬 선택된 프레임 미리보기")

    selected_indices = st.session_state.selected_frame_indices

    if selected_indices:
        selected_frames = [frames[i] for i in sorted(selected_indices)]

        col1, col2 = st.columns([2, 1])
        with col1:
            # GIF로 변환하여 애니메이션 표시
            gif_buffer = io.BytesIO()
            gif_frames = create_clean_gif_frames(selected_frames)

            if gif_frames:
                first_frame, first_trans = gif_frames[0]
                append_frames = [f[0] for f in gif_frames[1:]]
                first_frame.save(
                    gif_buffer, format="GIF", save_all=True,
                    append_images=append_frames,
                    duration=st.session_state.gif_speed, loop=0, disposal=2,
                    transparency=first_trans if first_trans is not None else 0
                )

            st.image(gif_buffer.getvalue(), caption=f"선택된 {len(selected_frames)}개 프레임")

        with col2:
            st.session_state.gif_speed = st.slider(
                "재생 속도 (ms)", 50, 300, st.session_state.gif_speed
            )
            st.info(f"✅ 선택: {len(selected_indices)} / 전체: {len(frames)}")
    else:
        st.info("프레임을 선택하면 여기에 애니메이션이 표시됩니다")

    st.markdown("---")

    # ===== 중단: 전체 선택/해제 버튼 =====
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ 전체 선택", use_container_width=True):
            st.session_state.selected_frame_indices = list(range(len(frames)))
            st.rerun()
    with col2:
        if st.button("❌ 전체 해제", use_container_width=True):
            st.session_state.selected_frame_indices = []
            st.rerun()
    with col3:
        if st.button("🔄 선택 반전", use_container_width=True):
            all_indices = set(range(len(frames)))
            selected = set(st.session_state.selected_frame_indices)
            st.session_state.selected_frame_indices = list(all_indices - selected)
            st.rerun()

    st.markdown("---")

    # ===== 하단: 프레임 그리드 =====
    st.subheader("🖼️ 프레임 선택")

    COLS_PER_ROW = 5
    THUMB_SIZE = 120

    for row_start in range(0, len(frames), COLS_PER_ROW):
        cols = st.columns(COLS_PER_ROW)
        for col_idx in range(COLS_PER_ROW):
            frame_idx = row_start + col_idx
            if frame_idx >= len(frames):
                break

            with cols[col_idx]:
                is_selected = frame_idx in st.session_state.selected_frame_indices

                # 썸네일 생성
                thumb = frames[frame_idx].copy()
                thumb.thumbnail((THUMB_SIZE, THUMB_SIZE))

                # 선택 상태에 따른 스타일링
                if is_selected:
                    st.markdown(f"""
                        <div style="border:3px solid #30D158;border-radius:12px;padding:4px;">
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div style="border:2px solid #333;border-radius:12px;padding:4px;">
                    """, unsafe_allow_html=True)

                st.image(thumb, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

                # 체크박스
                checkbox_label = f"✓ #{frame_idx+1}" if is_selected else f"#{frame_idx+1}"
                new_value = st.checkbox(checkbox_label, value=is_selected, key=f"frame_{frame_idx}")

                if new_value and frame_idx not in st.session_state.selected_frame_indices:
                    st.session_state.selected_frame_indices.append(frame_idx)
                    st.rerun()
                elif not new_value and frame_idx in st.session_state.selected_frame_indices:
                    st.session_state.selected_frame_indices.remove(frame_idx)
                    st.rerun()

def render_download_ui():
    """다운로드 화면"""
    frames = st.session_state.processed_frames
    selected_indices = st.session_state.selected_frame_indices

    if not frames or not selected_indices:
        st.error("선택된 프레임이 없습니다")
        return

    selected_frames = [frames[i] for i in sorted(selected_indices)]

    st.subheader("📦 결과물 다운로드")
    st.info(f"✅ 선택된 프레임: {len(selected_frames)}개")

    # 미리보기
    col_gif, col_sheet = st.columns(2)

    with col_gif:
        st.markdown("#### 🎬 애니메이션")

        # GIF 생성
        gif_buffer = io.BytesIO()
        gif_frames = create_clean_gif_frames(selected_frames)

        if gif_frames:
            first_frame, first_trans = gif_frames[0]
            append_frames = [f[0] for f in gif_frames[1:]]
            first_frame.save(
                gif_buffer, format="GIF", save_all=True,
                append_images=append_frames,
                duration=st.session_state.gif_speed, loop=0, disposal=2,
                transparency=first_trans if first_trans is not None else 0
            )

        st.image(gif_buffer.getvalue())

        # APNG 생성
        apng_buffer = io.BytesIO()
        selected_frames[0].save(
            apng_buffer, format="PNG", save_all=True,
            append_images=selected_frames[1:],
            duration=st.session_state.gif_speed, loop=0
        )

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button("🎬 GIF", gif_buffer.getvalue(), "animation.gif", "image/gif", use_container_width=True)
        with dl_col2:
            st.download_button("🖼️ APNG (권장)", apng_buffer.getvalue(), "animation.png", "image/png", use_container_width=True,
                              help="APNG는 완벽한 투명도를 지원합니다.")

    with col_sheet:
        st.markdown("#### 📄 스프라이트 시트")

        sheet_cols = st.number_input("열 수 (0=가로 한 줄)", 0, len(selected_frames), 0)
        sprite_sheet = create_sprite_sheet(selected_frames, sheet_cols)
        sheet_buffer = io.BytesIO()
        sprite_sheet.save(sheet_buffer, format="PNG")

        st.image(sprite_sheet, caption=f"{sprite_sheet.width}x{sprite_sheet.height}")

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button("📄 PNG 저장", sheet_buffer.getvalue(), "sprite_sheet.png", "image/png", use_container_width=True)
        with dl_col2:
            # ZIP 다운로드
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for idx, img in enumerate(selected_frames):
                    img_arr = io.BytesIO()
                    img.save(img_arr, format="PNG")
                    zf.writestr(f"frame_{idx:03d}.png", img_arr.getvalue())
            st.download_button("📦 ZIP 저장", zip_buffer.getvalue(), "frames.zip", "application/zip", use_container_width=True)

# ============================================
# 메인 플로우
# ============================================
def main():
    st.set_page_config(page_title="🦖 Sprite Maker", layout="wide")
    apply_dark_theme_css()
    init_session()

    st.title("🦖 스프라이트 생성기")
    show_step_indicator(st.session_state.step)

    # ===== STEP 1: 소스 입력 =====
    if st.session_state.step == 1:
        st.subheader("📤 Step 1: 소스 입력")

        mode = st.radio(
            "모드 선택",
            ["🤖 AI 이미지→영상", "📹 영상 업로드"],
            horizontal=True,
            key="mode_selector"
        )
        st.session_state.mode = 'ai' if 'AI' in mode else 'video'

        if st.session_state.mode == 'ai':
            # 이미지 업로드 + AI 생성 옵션
            uploaded = st.file_uploader("이미지 업로드", type=['png', 'jpg', 'jpeg'], key="ai_img_uploader")

            if uploaded:
                st.session_state.uploaded_image = uploaded
                image = Image.open(uploaded)

                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(image, caption=f"업로드된 이미지 ({image.width}x{image.height})", use_container_width=True)

                with col2:
                    if not REPLICATE_API_TOKEN:
                        st.warning("⚠️ Replicate API 토큰이 설정되지 않았습니다.")
                        with st.expander("🔑 API 토큰 설정 방법", expanded=True):
                            st.markdown("""
**Streamlit Cloud 배포:**
1. 앱 우측 상단 메뉴 → Settings → Secrets
2. 아래 내용을 입력 후 Save:
```toml
REPLICATE_API_TOKEN = "your_token_here"
```

**로컬 실행:**
- 프로젝트 폴더에 `.env` 파일 생성
- `REPLICATE_API_TOKEN=your_token` 추가

🔗 [Replicate API 토큰 발급](https://replicate.com/account/api-tokens)
                            """)
                    else:
                        st.success("✅ API 토큰 설정됨")

                        with st.expander("🎬 AI 생성 옵션", expanded=True):
                            ai_prompt = st.text_input(
                                "프롬프트 (선택사항)",
                                placeholder="예: walking animation, running cycle...",
                                help="생성할 영상의 움직임을 설명하세요"
                            )
                            motion = st.slider("모션 강도", 1, 255, 60, help="높을수록 움직임 큼")
                            video_length = st.selectbox(
                                "비디오 길이",
                                ["14_frames_with_svd", "25_frames_with_svd_xt"],
                                index=1
                            )
                            ai_fps = st.slider("FPS", 1, 30, 30)

                        if st.button("🚀 AI 영상 생성", type="primary", use_container_width=True):
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
                                        motion_bucket_id=motion,
                                        fps=ai_fps
                                    )

                                    st.write("✅ 생성 완료! 다운로드 중...")

                                    response = requests.get(video_url)
                                    video_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                                    video_temp.write(response.content)
                                    video_temp.close()

                                    st.session_state.video_path = video_temp.name
                                    st.session_state.video_frames = extract_frames_from_video(video_temp.name)
                                    st.session_state.step = 2
                                    status.update(label="✅ AI 비디오 생성 완료!", state="complete")
                                    st.rerun()

                                except Exception as e:
                                    status.update(label="❌ 생성 실패", state="error")
                                    st.error(f"오류: {str(e)}")

        else:
            # 비디오 업로드
            uploaded_video = st.file_uploader("비디오 업로드", type=['mp4', 'mov', 'avi'], key="video_uploader")

            if uploaded_video:
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                tfile.write(uploaded_video.read())
                tfile.close()

                st.session_state.video_path = tfile.name
                st.session_state.video_frames = extract_frames_from_video(tfile.name)

                st.video(tfile.name)
                st.info(f"📹 총 {len(st.session_state.video_frames)}개 프레임")

                if st.button("➡️ 다음 단계로", type="primary", use_container_width=True):
                    st.session_state.step = 2
                    st.rerun()

    # ===== STEP 2: 영상 확인 =====
    elif st.session_state.step == 2:
        st.subheader("📹 Step 2: 영상 확인")

        if st.session_state.video_path and st.session_state.video_frames:
            st.video(st.session_state.video_path)
            st.info(f"📹 총 {len(st.session_state.video_frames)}개 프레임")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ 다시 선택", use_container_width=True):
                    reset_to_step(1)
                    st.rerun()
            with col2:
                if st.button("➡️ 배경 제거", type="primary", use_container_width=True):
                    st.session_state.step = 3
                    st.rerun()
        else:
            st.warning("영상이 로드되지 않았습니다.")
            if st.button("⬅️ 처음으로"):
                reset_to_step(1)
                st.rerun()

    # ===== STEP 3: 배경 제거 =====
    elif st.session_state.step == 3:
        st.subheader("⚙️ Step 3: 배경 제거 설정")

        if st.session_state.video_frames:
            first_frame = st.session_state.video_frames[0]
            render_background_removal_ui(first_frame)  # 공통 함수 사용

            st.markdown("---")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ 이전", use_container_width=True):
                    st.session_state.step = 2
                    st.rerun()
            with col2:
                if st.button("✨ 전체 프레임 처리", type="primary", use_container_width=True):
                    with st.spinner("처리 중..."):
                        process_all_frames()
                    st.session_state.step = 4
                    st.rerun()
        else:
            st.error("프레임이 없습니다.")

    # ===== STEP 4: 프레임 선택 =====
    elif st.session_state.step == 4:
        st.subheader("🖼️ Step 4: 프레임 선택")

        render_frame_selection_ui()  # 공통 함수 사용

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ 배경 다시 설정", use_container_width=True):
                st.session_state.step = 3
                st.rerun()
        with col2:
            if st.session_state.selected_frame_indices:
                if st.button("➡️ 다운로드", type="primary", use_container_width=True):
                    st.session_state.step = 5
                    st.rerun()
            else:
                st.button("➡️ 다운로드", type="primary", use_container_width=True, disabled=True)
                st.caption("프레임을 선택해주세요")

    # ===== STEP 5: 다운로드 =====
    elif st.session_state.step == 5:
        st.subheader("📥 Step 5: 다운로드")

        render_download_ui()

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ 프레임 다시 선택", use_container_width=True):
                st.session_state.step = 4
                st.rerun()
        with col2:
            if st.button("🔄 처음부터", use_container_width=True):
                reset_to_step(1)
                st.rerun()

if __name__ == "__main__":
    main()
