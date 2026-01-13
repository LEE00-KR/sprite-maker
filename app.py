import streamlit as st
import cv2
import numpy as np
import tempfile
import os
import zipfile
from PIL import Image, ImageDraw, ImageFilter
import io
import requests
import base64
import replicate

try:
    from streamlit_drawable_canvas import st_canvas
    CANVAS_AVAILABLE = True
except ImportError:
    CANVAS_AVAILABLE = False

# --- 배경 제거 함수 (에지 스무딩 포함) ---
def remove_background(image, target_color, tolerance, edge_smoothing=0):
    """배경색을 제거하고 투명하게 만듦"""
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

# --- 로고/워터마크 영역 제거 함수 ---
def remove_logo_area(image, regions):
    """지정된 영역을 투명하게 만듦"""
    if image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    for region in regions:
        x, y, w, h = int(region['x']), int(region['y']), int(region['width']), int(region['height'])
        x = max(0, x)
        y = max(0, y)
        w = min(w, image.shape[1] - x)
        h = min(h, image.shape[0] - y)
        if w > 0 and h > 0:
            image[y:y+h, x:x+w, 3] = 0
    return image

# --- 이미지 리사이즈 함수 ---
def resize_image(pil_img, target_width, target_height):
    """PIL 이미지를 지정된 크기로 리사이즈"""
    if target_width > 0 and target_height > 0:
        return pil_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    return pil_img

# --- 스프라이트 시트 생성 함수 ---
def create_sprite_sheet(images, columns=0):
    """이미지 리스트를 스프라이트 시트로 합침"""
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
        total_width = width * columns
        total_height = height * rows
        sheet = Image.new("RGBA", (total_width, total_height))
        for idx, img in enumerate(images):
            row = idx // columns
            col = idx % columns
            sheet.paste(img, (col * width, row * height))

    return sheet

# --- 좌표에서 색상 추출 ---
def get_color_at_position(image_rgb, x, y):
    """이미지에서 특정 좌표의 RGB 색상 반환"""
    if 0 <= x < image_rgb.shape[1] and 0 <= y < image_rgb.shape[0]:
        r, g, b = image_rgb[y, x]
        return f"#{r:02x}{g:02x}{b:02x}"
    return "#000000"

# --- AI 비디오 생성 함수 ---
def generate_video_from_image(image_file, api_token, video_length="25_frames_with_svd_xt", motion_bucket_id=127, fps=6):
    """Replicate API를 사용하여 이미지에서 비디오 생성"""
    os.environ["REPLICATE_API_TOKEN"] = api_token

    # 이미지를 base64로 인코딩
    image_bytes = image_file.getvalue()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    # 이미지 MIME 타입 결정
    image_file.seek(0)
    header = image_file.read(8)
    image_file.seek(0)

    if header[:8] == b'\x89PNG\r\n\x1a\n':
        mime_type = "image/png"
    elif header[:2] == b'\xff\xd8':
        mime_type = "image/jpeg"
    else:
        mime_type = "image/png"

    data_uri = f"data:{mime_type};base64,{base64_image}"

    # Replicate API 호출
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
    """비디오를 스프라이트 이미지로 변환"""
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

            processed_rgb = cv2.cvtColor(processed_cv, cv2.COLOR_BGRA2RGBA)
            pil_img = Image.fromarray(processed_rgb)

            if use_custom_size:
                pil_img = resize_image(pil_img, output_width, output_height)

            processed_pil_images.append(pil_img)
            extracted_count += 1

        frame_idx += 1

        if extracted_count >= max_frames:
            break

    cap.release()
    return processed_pil_images, total_frames

# ===== UI 설정 =====
st.set_page_config(page_title="Sprite Maker + AI", layout="wide")

# ===== 사이드바: API 설정 및 모드 선택 =====
with st.sidebar:
    st.header("🎮 스프라이트 메이커")

    # 모드 선택
    st.subheader("📌 모드 선택")
    app_mode = st.radio(
        "작업 모드",
        ["📹 비디오 업로드", "🤖 AI 생성 (이미지→비디오)"],
        key="app_mode"
    )

    st.markdown("---")

    # AI 모드일 때만 API 키 입력 표시
    if "AI 생성" in app_mode:
        st.subheader("🔑 Replicate API")
        api_token = st.text_input(
            "API Token",
            type="password",
            placeholder="r8_xxxx...",
            help="https://replicate.com/account/api-tokens 에서 발급"
        )

        if not api_token:
            st.warning("⚠️ API Token을 입력해주세요")

        st.markdown("---")

        # AI 생성 설정
        st.subheader("🎬 AI 비디오 설정")
        video_length = st.selectbox(
            "비디오 길이",
            ["14_frames_with_svd", "25_frames_with_svd_xt"],
            index=1,
            help="프레임 수 선택"
        )

        motion_bucket_id = st.slider(
            "모션 강도",
            1, 255, 127,
            help="높을수록 움직임이 큼"
        )

        ai_fps = st.slider(
            "AI 비디오 FPS",
            1, 30, 6,
            help="생성될 비디오의 FPS"
        )

    st.markdown("---")

    # 공통 설정
    st.subheader("⚙️ 변환 설정")

    bg_color_hex = st.color_picker("제거할 배경색", "#000000")
    tolerance = st.slider("민감도", 0, 150, 100)
    edge_smoothing = st.slider("경계선 부드럽게", 0, 10, 3)

    st.markdown("---")

    st.subheader("📐 출력 설정")
    use_custom_size = st.checkbox("크기 직접 지정", value=False)
    if use_custom_size:
        col1, col2 = st.columns(2)
        with col1:
            output_width = st.number_input("너비", 1, 4096, 256)
        with col2:
            output_height = st.number_input("높이", 1, 4096, 256)
    else:
        output_width = 0
        output_height = 0

    st.markdown("---")

    st.subheader("🎞️ 프레임 추출")
    frame_interval = st.number_input("추출 간격", 1, 30, 1)
    max_frames = st.number_input("최대 프레임", 1, 500, 100)

    st.markdown("---")

    st.subheader("🎬 GIF 속도")
    gif_speed = st.slider("ms/프레임", 10, 500, 100, 10)

# ===== 메인 영역 =====
st.header("🦖 스프라이트 생성기")

# 세션 상태 초기화
if 'logo_regions' not in st.session_state:
    st.session_state.logo_regions = []
if 'picked_color' not in st.session_state:
    st.session_state.picked_color = "#000000"
if 'processed_images' not in st.session_state:
    st.session_state.processed_images = []

bg_color_rgb = tuple(int(bg_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

# ===== 비디오 업로드 모드 =====
if "비디오 업로드" in app_mode:
    st.subheader("📹 비디오 업로드 모드")

    uploaded_file = st.file_uploader(
        "영상 파일 업로드 (MP4/MOV/AVI)",
        type=["mp4", "mov", "avi"],
        key="video_uploader"
    )

    if uploaded_file is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(uploaded_file.read())
        tfile.close()

        cap = cv2.VideoCapture(tfile.name)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        ret, first_frame = cap.read()
        first_frame_rgb = None
        if ret:
            first_frame_rgb = cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)

        cap.release()

        st.info(f"📹 영상 정보: {original_width}x{original_height} | {total_frames}프레임 | {original_fps:.1f}fps")

        if first_frame_rgb is not None:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.image(first_frame_rgb, caption="첫 프레임 미리보기", use_container_width=True)
            with col2:
                st.markdown("### 워터마크 영역")
                if st.session_state.logo_regions:
                    for idx, region in enumerate(st.session_state.logo_regions):
                        st.text(f"#{idx+1}: ({region['x']:.0f}, {region['y']:.0f})")
                        if st.button("삭제", key=f"del_{idx}"):
                            st.session_state.logo_regions.pop(idx)
                            st.rerun()

        if st.button("✨ 변환 시작", type="primary", use_container_width=True):
            with st.spinner("비디오 처리 중..."):
                final_width = output_width if use_custom_size else original_width
                final_height = output_height if use_custom_size else original_height

                processed_images, _ = process_video_to_sprites(
                    tfile.name, bg_color_rgb, tolerance, edge_smoothing,
                    frame_interval, max_frames, use_custom_size,
                    final_width, final_height, st.session_state.logo_regions
                )

                st.session_state.processed_images = processed_images
                st.session_state.gif_speed = gif_speed

            st.success(f"✅ 변환 완료! {len(processed_images)}개 프레임")

        os.unlink(tfile.name)

# ===== AI 생성 모드 =====
else:
    st.subheader("🤖 AI 생성 모드 (이미지 → 비디오 → 스프라이트)")

    st.markdown("""
    **사용법:**
    1. 정적 이미지(PNG/JPG) 업로드
    2. AI가 이미지를 애니메이션 비디오로 변환
    3. 자동으로 스프라이트 시트 생성
    """)

    uploaded_image = st.file_uploader(
        "이미지 파일 업로드 (PNG/JPG)",
        type=["png", "jpg", "jpeg"],
        key="image_uploader"
    )

    if uploaded_image is not None:
        # 이미지 미리보기
        image = Image.open(uploaded_image)
        col1, col2 = st.columns([1, 1])

        with col1:
            st.image(image, caption="업로드된 이미지", use_container_width=True)
            st.caption(f"크기: {image.width}x{image.height}")

        with col2:
            st.markdown("### AI 생성 설정 요약")
            st.write(f"- 비디오 길이: {video_length if 'video_length' in dir() else '25_frames_with_svd_xt'}")
            st.write(f"- 모션 강도: {motion_bucket_id if 'motion_bucket_id' in dir() else 127}")
            st.write(f"- FPS: {ai_fps if 'ai_fps' in dir() else 6}")

        # API 토큰 체크
        if not api_token:
            st.error("❌ 사이드바에서 Replicate API Token을 입력해주세요!")
        else:
            if st.button("🚀 AI 비디오 생성 & 스프라이트 변환", type="primary", use_container_width=True):

                # 1단계: AI 비디오 생성
                with st.status("🤖 AI 비디오 생성 중...", expanded=True) as status:
                    st.write("⏳ Stable Video Diffusion 모델 실행 중...")
                    st.write("   (약 2~5분 소요될 수 있습니다)")

                    try:
                        uploaded_image.seek(0)
                        video_url = generate_video_from_image(
                            uploaded_image,
                            api_token,
                            video_length=video_length,
                            motion_bucket_id=motion_bucket_id,
                            fps=ai_fps
                        )

                        st.write("✅ 비디오 생성 완료!")
                        st.write(f"📥 비디오 다운로드 중...")

                        # 비디오 다운로드
                        response = requests.get(video_url)
                        video_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                        video_temp.write(response.content)
                        video_temp.close()

                        status.update(label="✅ AI 비디오 생성 완료!", state="complete")

                    except Exception as e:
                        status.update(label="❌ AI 생성 실패", state="error")
                        st.error(f"오류: {str(e)}")
                        st.stop()

                # 생성된 비디오 미리보기
                st.subheader("🎬 생성된 AI 비디오")
                st.video(video_temp.name)

                # 2단계: 스프라이트 변환
                with st.spinner("🎨 스프라이트 시트 생성 중..."):
                    cap = cv2.VideoCapture(video_temp.name)
                    ai_video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    ai_video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cap.release()

                    final_width = output_width if use_custom_size else ai_video_width
                    final_height = output_height if use_custom_size else ai_video_height

                    processed_images, total = process_video_to_sprites(
                        video_temp.name, bg_color_rgb, tolerance, edge_smoothing,
                        frame_interval, max_frames, use_custom_size,
                        final_width, final_height, []
                    )

                    st.session_state.processed_images = processed_images
                    st.session_state.gif_speed = gif_speed

                os.unlink(video_temp.name)
                st.success(f"✅ 스프라이트 변환 완료! {len(processed_images)}개 프레임")

# ===== 결과 표시 =====
if st.session_state.processed_images:
    processed_pil_images = st.session_state.processed_images
    current_gif_speed = st.session_state.get('gif_speed', 100)

    st.markdown("---")
    st.header("📦 결과물")

    tab1, tab2, tab3 = st.tabs(["🎬 GIF 미리보기", "📥 스프라이트 시트", "🖼️ 프레임 선택"])

    with tab1:
        gif_buffer = io.BytesIO()
        processed_pil_images[0].save(
            gif_buffer, format="GIF", save_all=True,
            append_images=processed_pil_images[1:],
            duration=current_gif_speed, loop=0, disposal=2, transparency=0
        )
        st.image(gif_buffer.getvalue(), caption="투명 배경 GIF")
        st.caption("💡 배경이 검게 보이면 다크모드 때문입니다.")

        st.download_button(
            "🎬 GIF 다운로드",
            gif_buffer.getvalue(),
            "animation.gif",
            "image/gif",
            use_container_width=True
        )

    with tab2:
        sheet_columns = st.number_input(
            "열 수 (0=가로 한 줄)", 0, len(processed_pil_images), 0,
            key="sheet_cols"
        )

        sprite_sheet = create_sprite_sheet(processed_pil_images, sheet_columns)
        sheet_buffer = io.BytesIO()
        sprite_sheet.save(sheet_buffer, format="PNG")

        st.image(sprite_sheet, caption=f"스프라이트 시트 ({sprite_sheet.width}x{sprite_sheet.height})")

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📄 스프라이트 시트(.png)",
                sheet_buffer.getvalue(),
                "sprite_sheet.png",
                "image/png",
                use_container_width=True
            )
        with col2:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for idx, img in enumerate(processed_pil_images):
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format="PNG")
                    zf.writestr(f"frame_{idx:03d}.png", img_byte_arr.getvalue())

            st.download_button(
                "📦 낱개 프레임(.zip)",
                zip_buffer.getvalue(),
                "frames.zip",
                "application/zip",
                use_container_width=True
            )

    with tab3:
        st.subheader("프레임 선택")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 전체 선택", use_container_width=True):
                st.session_state.selected_frames = list(range(len(processed_pil_images)))
                st.rerun()
        with col2:
            if st.button("❌ 전체 해제", use_container_width=True):
                st.session_state.selected_frames = []
                st.rerun()

        if 'selected_frames' not in st.session_state:
            st.session_state.selected_frames = list(range(len(processed_pil_images)))

        cols_per_row = 6
        total_images = len(processed_pil_images)

        for row_start in range(0, total_images, cols_per_row):
            cols = st.columns(cols_per_row)
            for col_idx, img_idx in enumerate(range(row_start, min(row_start + cols_per_row, total_images))):
                with cols[col_idx]:
                    is_selected = img_idx in st.session_state.selected_frames
                    if st.checkbox(f"#{img_idx+1}", value=is_selected, key=f"sel_{img_idx}"):
                        if img_idx not in st.session_state.selected_frames:
                            st.session_state.selected_frames.append(img_idx)
                            st.session_state.selected_frames.sort()
                    else:
                        if img_idx in st.session_state.selected_frames:
                            st.session_state.selected_frames.remove(img_idx)

                    thumb = processed_pil_images[img_idx].copy()
                    thumb.thumbnail((80, 80))
                    st.image(thumb)

        st.markdown("---")
        selected_indices = st.session_state.selected_frames
        st.info(f"선택: {len(selected_indices)}개")

        if selected_indices:
            selected_images = [processed_pil_images[i] for i in selected_indices]
            custom_columns = st.number_input(
                "커스텀 시트 열 수", 0, len(selected_images), 0,
                key="custom_cols"
            )

            custom_sheet = create_sprite_sheet(selected_images, custom_columns)
            custom_buffer = io.BytesIO()
            custom_sheet.save(custom_buffer, format="PNG")

            st.image(custom_sheet, caption=f"선택 프레임 시트 ({custom_sheet.width}x{custom_sheet.height})")
            st.download_button(
                "📄 선택 프레임 시트(.png)",
                custom_buffer.getvalue(),
                "custom_sprite_sheet.png",
                "image/png",
                use_container_width=True
            )
