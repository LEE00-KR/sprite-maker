import streamlit as st
import cv2
import numpy as np
import tempfile
import os
import zipfile
from PIL import Image, ImageDraw, ImageFilter
import io
from streamlit_drawable_canvas import st_canvas

# --- 배경 제거 함수 (에지 스무딩 포함) ---
def remove_background(image, target_color, tolerance, edge_smoothing=0):
    """
    배경색을 제거하고 투명하게 만듦
    edge_smoothing: 0=없음, 1~10=가우시안 블러 강도
    """
    image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    lower_bound = np.array([max(c - tolerance, 0) for c in target_color])
    upper_bound = np.array([min(c + tolerance, 255) for c in target_color])
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
    mask = cv2.inRange(rgb_image, lower_bound, upper_bound)
    mask_inv = cv2.bitwise_not(mask)

    # 에지 스무딩 적용
    if edge_smoothing > 0:
        # 가우시안 블러로 마스크 경계 부드럽게
        blur_size = edge_smoothing * 2 + 1  # 홀수로 만듦
        mask_inv = cv2.GaussianBlur(mask_inv, (blur_size, blur_size), 0)

        # 추가: 모폴로지 연산으로 경계 정리
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
        # 경계 체크
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

# --- 스프라이트 시트 생성 함수 (격자 지원) ---
def create_sprite_sheet(images, columns=0):
    """이미지 리스트를 스프라이트 시트로 합침. columns=0이면 가로 1줄"""
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

# --- UI 설정 ---
st.set_page_config(page_title="Sprite Maker", layout="wide")

st.header("🦖 스프라이트 생성기")

# 파일 업로드
uploaded_file = st.file_uploader("영상 파일 업로드 (MP4/MOV/AVI)", type=["mp4", "mov", "avi"])

if uploaded_file is not None:
    # 파일 임시 저장
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    cap = cv2.VideoCapture(tfile.name)

    # 영상 정보 가져오기
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 첫 프레임 읽기
    ret, first_frame = cap.read()
    first_frame_rgb = None
    if ret:
        first_frame_rgb = cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)

    # 영상 정보 표시
    st.info(f"📹 영상 정보: {original_width}x{original_height} | {total_frames}프레임 | {original_fps:.1f}fps")

    # ===== 2열 레이아웃: 왼쪽=이미지+캔버스, 오른쪽=설정 =====
    col_main, col_settings = st.columns([2, 1])

    # ===== 세션 상태 초기화 =====
    if 'logo_regions' not in st.session_state:
        st.session_state.logo_regions = []
    if 'picked_color' not in st.session_state:
        st.session_state.picked_color = "#000000"
    if 'canvas_mode' not in st.session_state:
        st.session_state.canvas_mode = "view"  # view, eyedropper, draw_rect

    # ===== 오른쪽: 설정 패널 =====
    with col_settings:
        st.subheader("⚙️ 설정")

        # 캔버스 모드 선택
        st.markdown("### 🖱️ 도구 선택")
        tool_mode = st.radio(
            "작업 모드",
            ["보기", "🎨 스포이드 (색상 추출)", "🔲 영역 선택 (워터마크)"],
            horizontal=False,
            key="tool_mode_radio"
        )

        if tool_mode == "보기":
            st.session_state.canvas_mode = "view"
        elif "스포이드" in tool_mode:
            st.session_state.canvas_mode = "eyedropper"
            st.caption("💡 이미지를 클릭하면 해당 위치의 색상이 선택됩니다.")
        else:
            st.session_state.canvas_mode = "draw_rect"
            st.caption("💡 이미지에서 드래그하여 제거할 영역을 선택하세요.")

        st.markdown("---")

        # 배경 제거 설정
        st.markdown("### 🎨 배경 제거 설정")

        col_color, col_btn = st.columns([2, 1])
        with col_color:
            bg_color_hex = st.color_picker(
                "제거할 색상",
                st.session_state.picked_color,
                key="bg_color_picker"
            )
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.session_state.canvas_mode == "eyedropper":
                st.success("스포이드 ON")

        # 스포이드로 선택한 색상 표시
        if st.session_state.picked_color != "#000000":
            st.caption(f"🎯 스포이드 선택 색상: {st.session_state.picked_color}")

        tolerance = st.slider("민감도", 0, 150, 100, help="비슷한 색을 어디까지 지울지 결정 (높을수록 더 많이 제거)")

        # 에지 스무딩 옵션
        edge_smoothing = st.slider(
            "경계선 부드럽게",
            0, 10, 3,
            help="0=날카로움, 높을수록 경계가 부드러움 (안티앨리어싱)"
        )

        st.markdown("---")

        # 워터마크 제거 영역
        st.markdown("### 🚫 워터마크 제거 영역")

        if st.session_state.logo_regions:
            for idx, region in enumerate(st.session_state.logo_regions):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"#{idx+1}: ({region['x']:.0f}, {region['y']:.0f}) {region['width']:.0f}x{region['height']:.0f}")
                with col2:
                    if st.button("🗑️", key=f"del_region_{idx}"):
                        st.session_state.logo_regions.pop(idx)
                        st.rerun()

            if st.button("🗑️ 모두 삭제", use_container_width=True):
                st.session_state.logo_regions = []
                st.rerun()
        else:
            st.caption("영역이 없습니다. '영역 선택' 모드에서 드래그하세요.")

        st.markdown("---")

        # 출력 크기 설정
        st.markdown("### 📐 출력 크기")
        use_custom_size = st.checkbox("크기 직접 지정", value=False)

        if use_custom_size:
            col1, col2 = st.columns(2)
            with col1:
                output_width = st.number_input("너비", 1, 4096, original_width)
            with col2:
                output_height = st.number_input("높이", 1, 4096, original_height)
        else:
            output_width = original_width
            output_height = original_height

        st.markdown("---")

        # 프레임 추출 설정
        st.markdown("### 🎞️ 프레임 추출")
        col1, col2 = st.columns(2)
        with col1:
            frame_interval = st.number_input("추출 간격", 1, max(30, total_frames // 2), 1)
        with col2:
            max_frames = st.number_input("최대 프레임", 1, total_frames, min(total_frames, 100))

        estimated_frames = min((total_frames + frame_interval - 1) // frame_interval, max_frames)
        st.caption(f"📊 예상: {estimated_frames}개 프레임")

        st.markdown("---")

        # GIF 설정
        st.markdown("### 🎬 GIF 속도")
        gif_speed = st.slider("ms/프레임", 10, 500, 100, 10)

    # ===== 왼쪽: 메인 캔버스 영역 =====
    with col_main:
        if first_frame_rgb is not None:
            # 캔버스 크기 계산 (화면에 맞게 스케일링)
            max_canvas_width = 800
            scale = min(1.0, max_canvas_width / original_width)
            canvas_width = int(original_width * scale)
            canvas_height = int(original_height * scale)

            # 배경 이미지 준비
            pil_image = Image.fromarray(first_frame_rgb)
            if scale < 1.0:
                pil_image = pil_image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)

            # 기존 영역 오버레이 그리기
            overlay_image = pil_image.copy()
            draw = ImageDraw.Draw(overlay_image)
            for region in st.session_state.logo_regions:
                x = int(region['x'] * scale)
                y = int(region['y'] * scale)
                w = int(region['width'] * scale)
                h = int(region['height'] * scale)
                draw.rectangle([x, y, x+w, y+h], outline="red", width=2)
                draw.rectangle([x+1, y+1, x+w-1, y+h-1], outline="yellow", width=1)

            # 캔버스 모드에 따른 설정
            if st.session_state.canvas_mode == "eyedropper":
                drawing_mode = "point"
                stroke_color = "#00FF00"
            elif st.session_state.canvas_mode == "draw_rect":
                drawing_mode = "rect"
                stroke_color = "#FF0000"
            else:
                drawing_mode = "transform"
                stroke_color = "#000000"

            # 캔버스 렌더링
            canvas_result = st_canvas(
                fill_color="rgba(255, 0, 0, 0.1)",
                stroke_width=2,
                stroke_color=stroke_color,
                background_image=overlay_image,
                update_streamlit=True,
                height=canvas_height,
                width=canvas_width,
                drawing_mode=drawing_mode,
                key="main_canvas",
            )

            # 캔버스 이벤트 처리
            if canvas_result.json_data is not None:
                objects = canvas_result.json_data.get("objects", [])

                if objects:
                    latest_obj = objects[-1]

                    # 스포이드 모드: 클릭한 위치의 색상 추출
                    if st.session_state.canvas_mode == "eyedropper" and latest_obj.get("type") == "circle":
                        cx = int(latest_obj.get("left", 0) / scale)
                        cy = int(latest_obj.get("top", 0) / scale)
                        picked = get_color_at_position(first_frame_rgb, cx, cy)
                        if picked != st.session_state.picked_color:
                            st.session_state.picked_color = picked
                            st.rerun()

                    # 영역 선택 모드: 사각형 추가
                    elif st.session_state.canvas_mode == "draw_rect" and latest_obj.get("type") == "rect":
                        rect_x = latest_obj.get("left", 0) / scale
                        rect_y = latest_obj.get("top", 0) / scale
                        rect_w = latest_obj.get("width", 0) * latest_obj.get("scaleX", 1) / scale
                        rect_h = latest_obj.get("height", 0) * latest_obj.get("scaleY", 1) / scale

                        if rect_w > 5 and rect_h > 5:  # 최소 크기 체크
                            new_region = {
                                'x': rect_x,
                                'y': rect_y,
                                'width': rect_w,
                                'height': rect_h
                            }
                            # 중복 방지
                            is_duplicate = False
                            for existing in st.session_state.logo_regions:
                                if (abs(existing['x'] - rect_x) < 5 and
                                    abs(existing['y'] - rect_y) < 5):
                                    is_duplicate = True
                                    break
                            if not is_duplicate:
                                st.session_state.logo_regions.append(new_region)
                                st.rerun()

            # 미리보기 정보
            st.caption(f"🖼️ 미리보기 (스케일: {scale*100:.0f}%) | 선택된 색상: {bg_color_hex}")

    # Hex -> RGB 변환
    bg_color_rgb = tuple(int(bg_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

    # ===== 변환 버튼 =====
    st.markdown("---")
    if st.button("✨ 변환 시작하기", type="primary", use_container_width=True):
        status_area = st.empty()
        status_area.info("영상을 프레임 단위로 처리 중...")

        progress_bar = st.progress(0)
        processed_pil_images = []

        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        frame_idx = 0
        extracted_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0 and extracted_count < max_frames:
                # 로고 영역 제거
                if st.session_state.logo_regions:
                    frame = remove_logo_area(frame, st.session_state.logo_regions)
                    processed_cv = frame.copy()
                    rgb_image = cv2.cvtColor(processed_cv, cv2.COLOR_BGRA2RGB)
                    lower_bound = np.array([max(c - tolerance, 0) for c in bg_color_rgb])
                    upper_bound = np.array([min(c + tolerance, 255) for c in bg_color_rgb])
                    mask = cv2.inRange(rgb_image, lower_bound, upper_bound)
                    mask_inv = cv2.bitwise_not(mask)

                    # 에지 스무딩
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
            if total_frames > 0:
                progress_bar.progress(min(frame_idx / total_frames, 1.0))

            if extracted_count >= max_frames:
                break

        status_area.success(f"✅ 변환 완료! {extracted_count}개 프레임")
        progress_bar.empty()

        st.session_state.processed_images = processed_pil_images
        st.session_state.gif_speed = gif_speed

    # ===== 결과 표시 =====
    if 'processed_images' in st.session_state and st.session_state.processed_images:
        processed_pil_images = st.session_state.processed_images
        current_gif_speed = st.session_state.get('gif_speed', 100)

        tab1, tab2, tab3 = st.tabs(["🎬 GIF 미리보기", "📥 스프라이트 시트", "🖼️ 프레임 선택"])

        with tab1:
            gif_buffer = io.BytesIO()
            processed_pil_images[0].save(
                gif_buffer, format="GIF", save_all=True,
                append_images=processed_pil_images[1:],
                duration=current_gif_speed, loop=0, disposal=2, transparency=0
            )
            st.image(gif_buffer.getvalue(), caption="투명 배경 적용됨")
            st.caption("💡 배경이 검게 보이면 다크모드 때문입니다. (실제로는 투명)")

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

    cap.release()
    tfile.close()
    os.unlink(tfile.name)
