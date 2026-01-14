# 🎮 Sprite Puppet Animator

이미지를 업로드하여 배경을 제거하고, 퍼펫 리깅을 통해 애니메이션을 만들어 스프라이트시트/GIF로 내보내는 웹 애플리케이션

## 🛠 기술 스택

| Frontend | Backend |
|----------|---------|
| React 18 | Python FastAPI |
| Vite | MongoDB (Motor) |
| Zustand (상태관리) | rembg (배경제거) |
| Lucide Icons | Pillow, OpenCV |

## 📁 프로젝트 구조

```
sprite-maker/
├── .devcontainer/              # Dev Container 설정
├── .env.example                # 환경변수 예제
│
└── sprite-puppet-animator/     # 메인 앱
    │
    ├── frontend/               # React + Vite
    │   ├── src/
    │   │   ├── components/
    │   │   │   ├── Canvas/     # BackgroundRemoval, PuppetWorkspace
    │   │   │   ├── LayerPanel/ # 레이어 패널
    │   │   │   ├── Timeline/   # 타임라인 + 키프레임
    │   │   │   ├── Toolbar/    # 도구 모음
    │   │   │   ├── Modal/      # ExportModal, CharacterModal
    │   │   │   └── Upload/     # 드래그앤드롭 업로드
    │   │   ├── stores/
    │   │   │   └── useStore.js # Zustand (Undo/Redo 포함)
    │   │   ├── utils/
    │   │   │   ├── api.js      # API 통신
    │   │   │   ├── animation.js # 키프레임 보간 엔진
    │   │   │   └── frameCapture.js # 프레임 캡처
    │   │   └── styles/
    │   │       └── index.css   # 다크 테마 스타일
    │   ├── package.json
    │   └── vite.config.js
    │
    └── backend/                # Python FastAPI
        ├── app/
        │   ├── api/            # 라우터 (characters, motions, image, export)
        │   ├── models/         # MongoDB 모델 (Character, Motion)
        │   ├── services/       # image_processing, export_service
        │   ├── main.py
        │   ├── config.py
        │   └── database.py
        ├── .env.example
        └── requirements.txt
```

## 🚀 시작하기

### 1. Backend 설정

```bash
cd sprite-puppet-animator/backend

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env에서 MONGODB_URL 설정

# 서버 실행
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend 설정

```bash
cd sprite-puppet-animator/frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

### 3. 접속

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 🎨 주요 기능

### Step 1: 이미지 업로드
- 드래그 앤 드롭 또는 클릭으로 업로드
- PNG, JPG, JPEG, WEBP 지원 (최대 10MB)

### Step 2: 배경 제거
- rembg AI 기반 자동 배경 제거
- 허용 오차 및 엣지 부드러움 조절

### Step 3: 퍼펫 작업
- **레이어 관리**: 추가, 삭제, 가시성 토글, 순서 변경
- **관절 추가** (J): 클릭하여 관절점 배치
- **뼈대 연결** (B): 두 관절을 연결
- **타임라인**: 키프레임 기반 애니메이션

### 애니메이션 엔진
- 키프레임 보간 (Linear, Ease-in/out, Elastic, Bounce)
- 실시간 프리뷰 재생
- 관절 드래그로 직접 포즈 수정

### 내보내기
- 스프라이트시트 (PNG) - 열 수, 간격 설정
- GIF 애니메이션 - FPS, 반복 설정
- PNG 시퀀스 (ZIP)

### 저장/불러오기
- 서버 저장 (MongoDB)
- JSON 로컬 저장/불러오기
- 미저장 상태 표시

## ⌨️ 단축키

| 키 | 기능 |
|----|------|
| V | 선택 도구 |
| M | 이동 도구 |
| J | 관절 추가 |
| B | 뼈대 연결 |
| Space | 재생/일시정지 |
| Ctrl+Z | 실행 취소 |
| Ctrl+Y / Ctrl+Shift+Z | 다시 실행 |
| Alt+드래그 | 캔버스 이동 |
| 휠 | 확대/축소 |

## 📡 API 엔드포인트

### Characters
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/characters` | 캐릭터 목록 |
| POST | `/api/characters` | 캐릭터 생성 |
| GET | `/api/characters/{id}` | 캐릭터 상세 |
| PUT | `/api/characters/{id}` | 캐릭터 수정 |
| DELETE | `/api/characters/{id}` | 캐릭터 삭제 |

### Image Processing
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/image/remove-background` | 배경 제거 |
| POST | `/api/image/cut-layer` | 레이어 분리 |
| POST | `/api/image/fill` | 영역 채우기 |

### Export
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/export/spritesheet` | 스프라이트시트 생성 |
| POST | `/api/export/gif` | GIF 생성 |
| POST | `/api/export/png-sequence` | PNG 시퀀스 (ZIP) |

## 📝 라이선스

MIT License
