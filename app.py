import streamlit as st
import cv2
import numpy as np
import tempfile
import os
import zipfile
from PIL import Image, ImageDraw
import io

# --- 배경 제거 함수 ---
def remove_background(image, target_color, tolerance):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    lower_bound = np.array([max(c - tolerance, 0) for c in target_color])
    upper_bound = np.array([min(c + tolerance, 255) for c in target_color])
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
    mask = cv2.inRange(rgb_image, lower_bound, upper_bound)
    mask_inv = cv2.bitwise_not(mask)
    image[:, :, 3] = mask_inv
    return image

# --- 로고/워터마크 영역 제거 함수 ---
def remove_logo_area(image, regions):
    """지정된 영역을 투명하게 만듦"""
    if image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    for region in regions:
        x, y, w, h = region['x'], region['y'], region['width'], region['height']
        # 해당 영역의 알파 채널을 0으로 설정 (투명)
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
        # 가로 한 줄 모드
        total_width = width * total_images
        sheet = Image.new("RGBA", (total_width, height))
        for idx, img in enumerate(images):
            sheet.paste(img, (idx * width, 0))
    else:
        # 격자 모드
        rows = (total_images + columns - 1) // columns
        total_width = width * columns
        total_height = height * rows
        sheet = Image.new("RGBA", (total_width, total_height))
        for idx, img in enumerate(images):
            row = idx // columns
            col = idx % columns
            sheet.paste(img, (col * width, row * height))

    return sheet

# --- UI 설정 ---
st.set_page_config(page_title="Sprite Maker", layout="centered")

st.header("🦖 스프라이트 생성기")
st.caption("비디오를 넣으면 투명 배경 스프라이트로 변환합니다.")

# 1. 파일 업로드
uploaded_file = st.file_uploader("1. 영상 파일 업로드 (MP4/MOV/AVI)", type=["mp4", "mov", "avi"])

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

    # ========== 설정 패널들 ==========

    # 2. 출력 크기 설정
    with st.expander("📐 출력 크기 설정", expanded=True):
        use_custom_size = st.checkbox("출력 크기 직접 지정", value=False)

        col1, col2 = st.columns(2)
        with col1:
            output_width = st.number_input(
                "너비 (px)",
                min_value=1,
                max_value=4096,
                value=original_width,
                disabled=not use_custom_size,
                help="출력 이미지의 가로 픽셀 수"
            )
        with col2:
            output_height = st.number_input(
                "높이 (px)",
                min_value=1,
                max_value=4096,
                value=original_height,
                disabled=not use_custom_size,
                help="출력 이미지의 세로 픽셀 수"
            )

        if use_custom_size:
            st.caption(f"✅ 출력 크기: {output_width}x{output_height} (원본: {original_width}x{original_height})")
        else:
            output_width = original_width
            output_height = original_height

    # 3. 프레임 추출 설정
    with st.expander("🎞️ 프레임 추출 설정", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            frame_interval = st.number_input(
                "프레임 추출 간격",
                min_value=1,
                max_value=max(30, total_frames // 2),
                value=1,
                help="N프레임마다 1개 추출 (1=모든 프레임, 2=절반, 3=1/3...)"
            )
        with col2:
            max_frames = st.number_input(
                "최대 프레임 수",
                min_value=1,
                max_value=total_frames,
                value=min(total_frames, 100),
                help="추출할 최대 프레임 개수 제한"
            )

        estimated_frames = min((total_frames + frame_interval - 1) // frame_interval, max_frames)
        st.caption(f"📊 예상 추출 프레임: 약 {estimated_frames}개 (전체 {total_frames}개 중)")

    # 4. GIF 설정
    with st.expander("🎬 GIF 애니메이션 설정", expanded=False):
        gif_speed = st.slider(
            "GIF 속도 (ms/프레임)",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
            help="프레임당 표시 시간 (작을수록 빠름)"
        )
        st.caption(f"⏱️ 예상 재생 시간: {(estimated_frames * gif_speed) / 1000:.1f}초")

    # 5. 배경 제거 설정
    with st.expander("⚙️ 배경 제거 설정", expanded=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            bg_color_hex = st.color_picker("제거할 색상", "#000000")
        with col2:
            tolerance = st.slider("민감도", 0, 150, 60, help="비슷한 색을 어디까지 지울지 결정")

    # 6. 로고/워터마크 제거 설정
    with st.expander("🚫 로고/워터마크 제거 영역", expanded=False):
        st.caption("영상 내 로고나 워터마크를 제거할 영역을 지정합니다. (여러 개 추가 가능)")

        # 세션 상태로 영역 관리
        if 'logo_regions' not in st.session_state:
            st.session_state.logo_regions = []

        # 새 영역 추가 UI
        st.markdown("**새 영역 추가:**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            new_x = st.number_input("X 좌표", min_value=0, max_value=original_width-1, value=0, key="new_x")
        with col2:
            new_y = st.number_input("Y 좌표", min_value=0, max_value=original_height-1, value=0, key="new_y")
        with col3:
            new_w = st.number_input("너비", min_value=1, max_value=original_width, value=100, key="new_w")
        with col4:
            new_h = st.number_input("높이", min_value=1, max_value=original_height, value=50, key="new_h")

        if st.button("➕ 영역 추가", use_container_width=True):
            st.session_state.logo_regions.append({
                'x': new_x, 'y': new_y, 'width': new_w, 'height': new_h
            })
            st.rerun()

        # 현재 등록된 영역 표시
        if st.session_state.logo_regions:
            st.markdown("**등록된 영역:**")
            for idx, region in enumerate(st.session_state.logo_regions):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"#{idx+1}: X={region['x']}, Y={region['y']}, W={region['width']}, H={region['height']}")
                with col2:
                    if st.button("삭제", key=f"del_{idx}"):
                        st.session_state.logo_regions.pop(idx)
                        st.rerun()

            if st.button("🗑️ 모든 영역 초기화", use_container_width=True):
                st.session_state.logo_regions = []
                st.rerun()

            # 미리보기에 영역 표시
            if first_frame_rgb is not None:
                preview_img = Image.fromarray(first_frame_rgb).copy()
                draw = ImageDraw.Draw(preview_img)
                for region in st.session_state.logo_regions:
                    x, y, w, h = region['x'], region['y'], region['width'], region['height']
                    draw.rectangle([x, y, x+w, y+h], outline="red", width=3)
                st.image(preview_img, caption="로고 제거 영역 미리보기 (빨간 박스)", use_container_width=True)
        else:
            st.caption("등록된 영역이 없습니다.")
            if first_frame_rgb is not None:
                st.image(first_frame_rgb, caption="원본 첫 프레임", use_container_width=True)

    # Hex -> RGB 변환
    bg_color_rgb = tuple(int(bg_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

    # ========== 변환 버튼 ==========
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

            # 프레임 간격 체크
            if frame_idx % frame_interval == 0 and extracted_count < max_frames:
                # 로고 영역 제거 (배경 제거 전)
                if st.session_state.logo_regions:
                    frame = remove_logo_area(frame, st.session_state.logo_regions)
                    processed_cv = frame.copy()
                    # 배경 제거 적용
                    rgb_image = cv2.cvtColor(processed_cv, cv2.COLOR_BGRA2RGB)
                    lower_bound = np.array([max(c - tolerance, 0) for c in bg_color_rgb])
                    upper_bound = np.array([min(c + tolerance, 255) for c in bg_color_rgb])
                    mask = cv2.inRange(rgb_image, lower_bound, upper_bound)
                    mask_inv = cv2.bitwise_not(mask)
                    # 기존 알파와 병합 (로고 영역 유지)
                    processed_cv[:, :, 3] = cv2.bitwise_and(processed_cv[:, :, 3], mask_inv)
                else:
                    processed_cv = remove_background(frame, bg_color_rgb, tolerance)

                processed_rgb = cv2.cvtColor(processed_cv, cv2.COLOR_BGRA2RGBA)
                pil_img = Image.fromarray(processed_rgb)

                # 크기 조정
                if use_custom_size:
                    pil_img = resize_image(pil_img, output_width, output_height)

                processed_pil_images.append(pil_img)
                extracted_count += 1

            frame_idx += 1
            if total_frames > 0:
                progress_bar.progress(min(frame_idx / total_frames, 1.0))

            # 최대 프레임 도달 시 조기 종료
            if extracted_count >= max_frames:
                break

        status_area.success(f"변환 완료! {extracted_count}개 프레임 추출됨")
        progress_bar.empty()

        # 세션 상태에 결과 저장
        st.session_state.processed_images = processed_pil_images
        st.session_state.gif_speed = gif_speed

    # ========== 결과 표시 (변환 후) ==========
    if 'processed_images' in st.session_state and st.session_state.processed_images:
        processed_pil_images = st.session_state.processed_images
        current_gif_speed = st.session_state.get('gif_speed', 100)

        # 결과 탭
        tab1, tab2, tab3 = st.tabs(["🎬 GIF 미리보기", "📥 스프라이트 시트", "🖼️ 프레임 선택"])

        # 탭 1: GIF 미리보기
        with tab1:
            gif_buffer = io.BytesIO()
            processed_pil_images[0].save(
                gif_buffer, format="GIF", save_all=True,
                append_images=processed_pil_images[1:],
                duration=current_gif_speed, loop=0, disposal=2, transparency=0
            )
            st.image(gif_buffer.getvalue(), caption="투명 배경 적용됨", use_container_width=True)
            st.caption("💡 배경이 검게 보이면 다크모드 때문일 수 있습니다. (실제로는 투명함)")

            st.download_button(
                label="🎬 GIF 다운로드",
                data=gif_buffer.getvalue(),
                file_name="animation.gif",
                mime="image/gif",
                use_container_width=True
            )

        # 탭 2: 스프라이트 시트
        with tab2:
            st.subheader("스프라이트 시트 설정")

            sheet_columns = st.number_input(
                "열 수 (0=가로 한 줄)",
                min_value=0,
                max_value=len(processed_pil_images),
                value=0,
                help="스프라이트 시트의 열 개수. 0이면 가로 한 줄로 배치"
            )

            sprite_sheet = create_sprite_sheet(processed_pil_images, sheet_columns)
            sheet_buffer = io.BytesIO()
            sprite_sheet.save(sheet_buffer, format="PNG")

            st.image(sprite_sheet, caption=f"스프라이트 시트 ({sprite_sheet.width}x{sprite_sheet.height})", use_container_width=True)

            st.download_button(
                label="📄 스프라이트 시트(.png) 저장",
                data=sheet_buffer.getvalue(),
                file_name="sprite_sheet.png",
                mime="image/png",
                use_container_width=True
            )

            st.markdown("---")

            # ZIP 생성
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for idx, img in enumerate(processed_pil_images):
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format="PNG")
                    zf.writestr(f"frame_{idx:03d}.png", img_byte_arr.getvalue())

            st.download_button(
                label="📦 낱개 프레임(.zip) 저장",
                data=zip_buffer.getvalue(),
                file_name="frames.zip",
                mime="application/zip",
                use_container_width=True
            )

        # 탭 3: 프레임 선택
        with tab3:
            st.subheader("스프라이트 시트에 포함할 프레임 선택")
            st.caption("원하는 프레임만 선택하여 커스텀 스프라이트 시트를 만들 수 있습니다.")

            # 전체 선택/해제 버튼
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 전체 선택", use_container_width=True):
                    st.session_state.selected_frames = list(range(len(processed_pil_images)))
                    st.rerun()
            with col2:
                if st.button("❌ 전체 해제", use_container_width=True):
                    st.session_state.selected_frames = []
                    st.rerun()

            # 선택 상태 초기화
            if 'selected_frames' not in st.session_state:
                st.session_state.selected_frames = list(range(len(processed_pil_images)))

            # 프레임 그리드 표시 (4열)
            cols_per_row = 4
            total_images = len(processed_pil_images)

            for row_start in range(0, total_images, cols_per_row):
                cols = st.columns(cols_per_row)
                for col_idx, img_idx in enumerate(range(row_start, min(row_start + cols_per_row, total_images))):
                    with cols[col_idx]:
                        is_selected = img_idx in st.session_state.selected_frames

                        # 체크박스
                        if st.checkbox(f"#{img_idx+1}", value=is_selected, key=f"frame_select_{img_idx}"):
                            if img_idx not in st.session_state.selected_frames:
                                st.session_state.selected_frames.append(img_idx)
                                st.session_state.selected_frames.sort()
                        else:
                            if img_idx in st.session_state.selected_frames:
                                st.session_state.selected_frames.remove(img_idx)

                        # 썸네일
                        thumb = processed_pil_images[img_idx].copy()
                        thumb.thumbnail((100, 100))
                        st.image(thumb, use_container_width=True)

            st.markdown("---")

            # 선택된 프레임으로 스프라이트 시트 생성
            selected_indices = st.session_state.selected_frames
            st.info(f"선택된 프레임: {len(selected_indices)}개")

            if selected_indices:
                selected_images = [processed_pil_images[i] for i in selected_indices]

                custom_columns = st.number_input(
                    "커스텀 시트 열 수 (0=가로 한 줄)",
                    min_value=0,
                    max_value=len(selected_images),
                    value=0,
                    key="custom_sheet_columns"
                )

                custom_sheet = create_sprite_sheet(selected_images, custom_columns)
                custom_buffer = io.BytesIO()
                custom_sheet.save(custom_buffer, format="PNG")

                st.image(custom_sheet, caption=f"선택된 프레임 시트 ({custom_sheet.width}x{custom_sheet.height})", use_container_width=True)

                st.download_button(
                    label="📄 선택 프레임 시트(.png) 저장",
                    data=custom_buffer.getvalue(),
                    file_name="custom_sprite_sheet.png",
                    mime="image/png",
                    use_container_width=True
                )

    cap.release()
    tfile.close()
    os.unlink(tfile.name)
