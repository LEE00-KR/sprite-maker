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
sprite-puppet-animator/
│
├── frontend/                      # React + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── Canvas/           # 캔버스 관련
│   │   │   ├── LayerPanel/       # 레이어 패널
│   │   │   ├── Timeline/         # 타임라인
│   │   │   ├── Toolbar/          # 도구 모음
│   │   │   ├── Modal/            # 모달
│   │   │   └── Upload/           # 업로드
│   │   ├── stores/
│   │   │   └── useStore.js       # Zustand 상태관리
│   │   ├── utils/
│   │   │   └── api.js            # API 통신
│   │   ├── styles/
│   │   │   └── index.css         # 스타일
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
└── backend/                       # Python FastAPI
    ├── app/
    │   ├── api/                  # API 라우터
    │   ├── models/               # MongoDB 모델
    │   ├── services/             # 비즈니스 로직
    │   ├── main.py
    │   └── config.py
    └── requirements.txt
```

## 🚀 시작하기

### 1. Backend 설정

```bash
cd backend

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env

# 서버 실행
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend 설정

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

### 3. 접속

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 🎨 주요 기능

### Step 1: 이미지 업로드
- 드래그 앤 드롭 또는 클릭으로 업로드
- PNG, JPG, JPEG, WEBP 지원 (최대 10MB)

### Step 2: 배경 제거
- rembg AI 기반 배경 제거
- 허용 오차 및 엣지 부드러움 조절

### Step 3: 퍼펫 작업
- **레이어 관리**: 추가, 삭제, 가시성 토글
- **관절 추가** (J): 클릭하여 관절점 배치
- **뼈대 연결** (B): 두 관절을 연결
- **타임라인**: 키프레임 애니메이션

### 내보내기
- 스프라이트시트 (PNG)
- GIF 애니메이션
- PNG 시퀀스 (ZIP)

## ⌨️ 단축키

| 키 | 기능 |
|----|------|
| V | 선택 도구 |
| M | 이동 도구 |
| J | 관절 추가 |
| B | 뼈대 연결 |
| Space | 재생/일시정지 |
| Ctrl+Z | 실행 취소 |
| Alt+드래그 | 캔버스 이동 |
| 휠 | 확대/축소 |

## 📡 API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/characters` | 캐릭터 목록 |
| POST | `/api/characters` | 캐릭터 생성 |
| GET | `/api/characters/{id}` | 캐릭터 상세 |
| POST | `/api/image/remove-background` | 배경 제거 |
| POST | `/api/export/spritesheet` | 스프라이트시트 |
| POST | `/api/export/gif` | GIF 생성 |

## 📝 라이선스

MIT License
