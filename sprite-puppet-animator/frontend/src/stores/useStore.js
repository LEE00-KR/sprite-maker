import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'

// Undo/Redo를 위한 상태 스냅샷 키
const UNDOABLE_KEYS = ['character', 'currentMotion']

// 히스토리 최대 크기
const MAX_HISTORY_SIZE = 50

// 초기 상태
const initialState = {
  // 현재 단계
  currentStep: 1,

  // 현재 도구
  currentTool: 'select',

  // 프로젝트 정보
  project: {
    id: null,
    name: '새 프로젝트',
    saved: true,
  },

  // 캐릭터 데이터
  character: {
    id: null,
    name: '',
    originalImage: null,
    processedImage: null,
    layers: [],
    joints: [],
    bones: [],
  },

  // 현재 모션
  currentMotion: {
    id: null,
    name: '새 모션',
    fps: 12,
    frameCount: 30,
    loop: true,
    keyframes: [],
  },

  // 선택 상태
  selection: {
    layers: [],
    joints: [],
    bones: [],
    keyframes: [],
  },

  // 타임라인 상태
  timeline: {
    currentFrame: 0,
    isPlaying: false,
    isLooping: true,
  },

  // 캔버스 상태
  canvas: {
    zoom: 1,
    panX: 0,
    panY: 0,
  },

  // UI 상태
  ui: {
    activeSubTab: 'layer',
    showExportModal: false,
    showCharacterModal: false,
  },

  // 로딩 상태
  isLoading: false,
  loadingMessage: '',

  // 토스트
  toasts: [],

  // Undo/Redo 히스토리
  history: {
    past: [],
    future: [],
  },
}

export const useStore = create((set, get) => ({
  ...initialState,

  // ==========================================
  // 앱 초기화
  // ==========================================
  initApp: () => {
    console.log('🎮 Sprite Puppet Animator 초기화')
  },

  // ==========================================
  // Undo/Redo 시스템
  // ==========================================

  // 현재 상태 스냅샷 저장
  saveSnapshot: () => {
    const state = get()
    const snapshot = {}
    UNDOABLE_KEYS.forEach((key) => {
      snapshot[key] = JSON.parse(JSON.stringify(state[key]))
    })

    set((s) => ({
      history: {
        past: [...s.history.past.slice(-MAX_HISTORY_SIZE + 1), snapshot],
        future: [], // 새 변경 시 redo 스택 초기화
      },
      project: { ...s.project, saved: false },
    }))
  },

  // Undo
  undo: () => {
    const state = get()
    if (state.history.past.length === 0) return

    // 현재 상태를 future에 저장
    const currentSnapshot = {}
    UNDOABLE_KEYS.forEach((key) => {
      currentSnapshot[key] = JSON.parse(JSON.stringify(state[key]))
    })

    // 이전 상태 가져오기
    const newPast = [...state.history.past]
    const previousSnapshot = newPast.pop()

    set({
      ...previousSnapshot,
      history: {
        past: newPast,
        future: [currentSnapshot, ...state.history.future.slice(0, MAX_HISTORY_SIZE - 1)],
      },
    })
  },

  // Redo
  redo: () => {
    const state = get()
    if (state.history.future.length === 0) return

    // 현재 상태를 past에 저장
    const currentSnapshot = {}
    UNDOABLE_KEYS.forEach((key) => {
      currentSnapshot[key] = JSON.parse(JSON.stringify(state[key]))
    })

    // 다음 상태 가져오기
    const newFuture = [...state.history.future]
    const nextSnapshot = newFuture.shift()

    set({
      ...nextSnapshot,
      history: {
        past: [...state.history.past, currentSnapshot],
        future: newFuture,
      },
    })
  },

  // Undo 가능 여부
  canUndo: () => get().history.past.length > 0,

  // Redo 가능 여부
  canRedo: () => get().history.future.length > 0,

  // ==========================================
  // 단계 관리
  // ==========================================
  setStep: (step) => set({ currentStep: step }),
  
  nextStep: () => set((state) => ({ 
    currentStep: Math.min(state.currentStep + 1, 3) 
  })),
  
  prevStep: () => set((state) => ({ 
    currentStep: Math.max(state.currentStep - 1, 1) 
  })),

  // ==========================================
  // 도구 관리
  // ==========================================
  setTool: (tool) => set({ currentTool: tool }),

  // ==========================================
  // 이미지 관리
  // ==========================================
  setOriginalImage: (imageData) => set((state) => ({
    character: {
      ...state.character,
      originalImage: imageData,
    },
  })),

  setProcessedImage: (imageData) => set((state) => ({
    character: {
      ...state.character,
      processedImage: imageData,
    },
  })),

  // ==========================================
  // 레이어 관리
  // ==========================================
  addLayer: (layer) => {
    get().saveSnapshot()
    set((state) => ({
      character: {
        ...state.character,
        layers: [
          ...state.character.layers,
          {
            id: uuidv4(),
            name: layer.name || `레이어 ${state.character.layers.length + 1}`,
            order: state.character.layers.length,
            imageData: layer.imageData || null,
            visible: true,
            opacity: 1,
            transform: { x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1 },
            ...layer,
          },
        ],
      },
    }))
  },

  updateLayer: (layerId, updates) => set((state) => ({
    character: {
      ...state.character,
      layers: state.character.layers.map((layer) =>
        layer.id === layerId ? { ...layer, ...updates } : layer
      ),
    },
  })),

  removeLayer: (layerId) => {
    get().saveSnapshot()
    set((state) => ({
      character: {
        ...state.character,
        layers: state.character.layers.filter((l) => l.id !== layerId),
      },
      selection: {
        ...state.selection,
        layers: state.selection.layers.filter((id) => id !== layerId),
      },
    }))
  },

  reorderLayers: (newOrder) => {
    get().saveSnapshot()
    set((state) => ({
      character: {
        ...state.character,
        layers: newOrder,
      },
    }))
  },

  // ==========================================
  // 관절 관리
  // ==========================================
  addJoint: (joint) => {
    get().saveSnapshot()
    set((state) => {
      const newJoint = {
        id: uuidv4(),
        name: joint.name || `관절 ${state.character.joints.length + 1}`,
        x: joint.x,
        y: joint.y,
        parentId: joint.parentId || null,
        layerId: joint.layerId || null,
        color: joint.color || '#ef4444',
      }
      return {
        character: {
          ...state.character,
          joints: [...state.character.joints, newJoint],
        },
      }
    })
  },

  updateJoint: (jointId, updates) => set((state) => ({
    character: {
      ...state.character,
      joints: state.character.joints.map((joint) =>
        joint.id === jointId ? { ...joint, ...updates } : joint
      ),
    },
    project: { ...state.project, saved: false },
  })),

  removeJoint: (jointId) => {
    get().saveSnapshot()
    set((state) => ({
      character: {
        ...state.character,
        joints: state.character.joints.filter((j) => j.id !== jointId),
        bones: state.character.bones.filter(
          (b) => b.startJointId !== jointId && b.endJointId !== jointId
        ),
      },
      selection: {
        ...state.selection,
        joints: state.selection.joints.filter((id) => id !== jointId),
      },
    }))
  },

  // ==========================================
  // 뼈대 관리
  // ==========================================
  addBone: (startJointId, endJointId) => {
    const state = get()
    // 이미 존재하는지 확인
    const exists = state.character.bones.some(
      (b) =>
        (b.startJointId === startJointId && b.endJointId === endJointId) ||
        (b.startJointId === endJointId && b.endJointId === startJointId)
    )
    if (exists) return

    get().saveSnapshot()
    const newBone = {
      id: uuidv4(),
      name: `뼈대 ${state.character.bones.length + 1}`,
      startJointId,
      endJointId,
    }
    set({
      character: {
        ...state.character,
        bones: [...state.character.bones, newBone],
      },
    })
  },

  removeBone: (boneId) => {
    get().saveSnapshot()
    set((state) => ({
      character: {
        ...state.character,
        bones: state.character.bones.filter((b) => b.id !== boneId),
      },
    }))
  },

  // ==========================================
  // 키프레임 관리
  // ==========================================
  addKeyframe: (jointId, frameNumber, props) => {
    const state = get()
    const existingIndex = state.currentMotion.keyframes.findIndex(
      (kf) => kf.jointId === jointId && kf.frameNumber === frameNumber
    )

    // 새 키프레임 추가 시에만 스냅샷 저장 (업데이트는 저장 안함 - 드래그 시 너무 많은 스냅샷 방지)
    if (existingIndex < 0) {
      get().saveSnapshot()
    }

    let newKeyframes
    if (existingIndex >= 0) {
      // 업데이트
      newKeyframes = [...state.currentMotion.keyframes]
      newKeyframes[existingIndex] = {
        ...newKeyframes[existingIndex],
        ...props,
      }
    } else {
      // 새로 추가
      newKeyframes = [
        ...state.currentMotion.keyframes,
        {
          id: uuidv4(),
          jointId,
          frameNumber,
          x: props.x || 0,
          y: props.y || 0,
          rotation: props.rotation || 0,
          easing: props.easing || 'linear',
          ...props,
        },
      ]
    }

    // 프레임 번호로 정렬
    newKeyframes.sort((a, b) => a.frameNumber - b.frameNumber)

    set({
      currentMotion: {
        ...state.currentMotion,
        keyframes: newKeyframes,
      },
      project: { ...state.project, saved: false },
    })
  },

  removeKeyframe: (keyframeId) => {
    get().saveSnapshot()
    set((state) => ({
      currentMotion: {
        ...state.currentMotion,
        keyframes: state.currentMotion.keyframes.filter(
          (kf) => kf.id !== keyframeId
        ),
      },
    }))
  },

  // ==========================================
  // 타임라인 관리
  // ==========================================
  setCurrentFrame: (frame) => set((state) => ({
    timeline: {
      ...state.timeline,
      currentFrame: Math.max(
        0,
        Math.min(frame, state.currentMotion.frameCount - 1)
      ),
    },
  })),

  setPlaying: (isPlaying) => set((state) => ({
    timeline: { ...state.timeline, isPlaying },
  })),

  togglePlay: () => set((state) => ({
    timeline: { ...state.timeline, isPlaying: !state.timeline.isPlaying },
  })),

  toggleLoop: () => set((state) => ({
    timeline: { ...state.timeline, isLooping: !state.timeline.isLooping },
  })),

  setFps: (fps) => set((state) => ({
    currentMotion: { ...state.currentMotion, fps },
  })),

  setFrameCount: (frameCount) => set((state) => ({
    currentMotion: { ...state.currentMotion, frameCount },
  })),

  // ==========================================
  // 선택 관리
  // ==========================================
  selectLayer: (layerId, multi = false) => set((state) => ({
    selection: {
      ...state.selection,
      layers: multi
        ? state.selection.layers.includes(layerId)
          ? state.selection.layers.filter((id) => id !== layerId)
          : [...state.selection.layers, layerId]
        : [layerId],
    },
  })),

  selectJoint: (jointId, multi = false) => set((state) => ({
    selection: {
      ...state.selection,
      joints: multi
        ? state.selection.joints.includes(jointId)
          ? state.selection.joints.filter((id) => id !== jointId)
          : [...state.selection.joints, jointId]
        : [jointId],
    },
  })),

  clearSelection: () => set((state) => ({
    selection: { layers: [], joints: [], bones: [], keyframes: [] },
  })),

  // ==========================================
  // 캔버스 관리
  // ==========================================
  setZoom: (zoom) => set((state) => ({
    canvas: {
      ...state.canvas,
      zoom: Math.max(0.1, Math.min(5, zoom)),
    },
  })),

  zoomIn: () => set((state) => ({
    canvas: {
      ...state.canvas,
      zoom: Math.min(state.canvas.zoom + 0.1, 5),
    },
  })),

  zoomOut: () => set((state) => ({
    canvas: {
      ...state.canvas,
      zoom: Math.max(state.canvas.zoom - 0.1, 0.1),
    },
  })),

  resetZoom: () => set((state) => ({
    canvas: { ...state.canvas, zoom: 1, panX: 0, panY: 0 },
  })),

  setPan: (panX, panY) => set((state) => ({
    canvas: { ...state.canvas, panX, panY },
  })),

  // ==========================================
  // UI 관리
  // ==========================================
  setActiveSubTab: (tab) => set((state) => ({
    ui: { ...state.ui, activeSubTab: tab },
  })),

  openExportModal: () => set((state) => ({
    ui: { ...state.ui, showExportModal: true },
  })),

  closeExportModal: () => set((state) => ({
    ui: { ...state.ui, showExportModal: false },
  })),

  openCharacterModal: () => set((state) => ({
    ui: { ...state.ui, showCharacterModal: true },
  })),

  closeCharacterModal: () => set((state) => ({
    ui: { ...state.ui, showCharacterModal: false },
  })),

  // ==========================================
  // 로딩 관리
  // ==========================================
  setLoading: (isLoading, message = '') => set({
    isLoading,
    loadingMessage: message,
  }),

  // ==========================================
  // 토스트 관리
  // ==========================================
  addToast: (message, type = 'info', duration = 3000) => {
    const id = uuidv4()
    set((state) => ({
      toasts: [...state.toasts, { id, message, type }],
    }))
    
    // 자동 제거
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }))
    }, duration)
  },

  removeToast: (id) => set((state) => ({
    toasts: state.toasts.filter((t) => t.id !== id),
  })),

  // ==========================================
  // 프로젝트 관리
  // ==========================================
  newProject: () => set({
    ...initialState,
    toasts: get().toasts, // 토스트는 유지
  }),

  setProjectName: (name) => set((state) => ({
    project: { ...state.project, name },
    character: { ...state.character, name },
  })),

  // ==========================================
  // 저장/불러오기
  // ==========================================

  // 캐릭터 데이터 로드
  loadCharacter: (characterData) => set((state) => ({
    character: {
      id: characterData.id || characterData._id || null,
      name: characterData.name || '',
      originalImage: characterData.original_image || characterData.originalImage || null,
      processedImage: characterData.processed_image || characterData.processedImage || null,
      layers: (characterData.layers || []).map((layer, index) => ({
        id: layer.id || layer._id || uuidv4(),
        name: layer.name || `레이어 ${index + 1}`,
        order: layer.order ?? index,
        imageData: layer.image_data || layer.imageData || null,
        visible: layer.visible ?? true,
        opacity: layer.opacity ?? 1,
        transform: layer.transform || { x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1 },
      })),
      joints: (characterData.joints || []).map((joint, index) => ({
        id: joint.id || joint._id || uuidv4(),
        name: joint.name || `관절 ${index + 1}`,
        x: joint.x || 0,
        y: joint.y || 0,
        parentId: joint.parent_id || joint.parentId || null,
        layerId: joint.layer_id || joint.layerId || null,
        color: joint.color || '#ef4444',
      })),
      bones: (characterData.bones || []).map((bone, index) => ({
        id: bone.id || bone._id || uuidv4(),
        name: bone.name || `뼈대 ${index + 1}`,
        startJointId: bone.start_joint_id || bone.startJointId,
        endJointId: bone.end_joint_id || bone.endJointId,
      })),
    },
    project: {
      ...state.project,
      id: characterData.id || characterData._id || null,
      name: characterData.name || '새 프로젝트',
      saved: true,
    },
    currentStep: 3, // 퍼펫 작업 단계로 이동
  })),

  // 모션 데이터 로드
  loadMotion: (motionData) => set(() => ({
    currentMotion: {
      id: motionData.id || motionData._id || null,
      name: motionData.name || '새 모션',
      fps: motionData.fps || 12,
      frameCount: motionData.frame_count || motionData.frameCount || 30,
      loop: motionData.loop ?? true,
      keyframes: (motionData.keyframes || []).map((kf) => ({
        id: kf.id || kf._id || uuidv4(),
        jointId: kf.joint_id || kf.jointId,
        frameNumber: kf.frame_number ?? kf.frameNumber ?? 0,
        x: kf.x || 0,
        y: kf.y || 0,
        rotation: kf.rotation || 0,
        easing: kf.easing || 'linear',
      })),
    },
  })),

  // 현재 상태를 저장용 객체로 변환
  getCharacterData: () => {
    const state = get()
    return {
      name: state.character.name || state.project.name || '미저장 캐릭터',
      original_image: state.character.originalImage,
      processed_image: state.character.processedImage,
      layers: state.character.layers.map((layer) => ({
        name: layer.name,
        order: layer.order,
        image_data: layer.imageData,
        visible: layer.visible,
        opacity: layer.opacity,
        transform: layer.transform,
      })),
      joints: state.character.joints.map((joint) => ({
        name: joint.name,
        x: joint.x,
        y: joint.y,
        parent_id: joint.parentId,
        layer_id: joint.layerId,
        color: joint.color,
      })),
      bones: state.character.bones.map((bone) => ({
        name: bone.name,
        start_joint_id: bone.startJointId,
        end_joint_id: bone.endJointId,
      })),
    }
  },

  // 현재 모션을 저장용 객체로 변환
  getMotionData: () => {
    const state = get()
    return {
      name: state.currentMotion.name,
      fps: state.currentMotion.fps,
      frame_count: state.currentMotion.frameCount,
      loop: state.currentMotion.loop,
      keyframes: state.currentMotion.keyframes.map((kf) => ({
        joint_id: kf.jointId,
        frame_number: kf.frameNumber,
        x: kf.x,
        y: kf.y,
        rotation: kf.rotation,
        easing: kf.easing,
      })),
    }
  },

  // 프로젝트 JSON 내보내기
  exportProjectAsJSON: () => {
    const state = get()
    return JSON.stringify({
      version: '1.0',
      project: state.project,
      character: state.getCharacterData(),
      motion: state.getMotionData(),
    }, null, 2)
  },

  // 프로젝트 JSON 가져오기
  importProjectFromJSON: (jsonString) => {
    try {
      const data = JSON.parse(jsonString)
      const state = get()

      if (data.character) {
        state.loadCharacter(data.character)
      }
      if (data.motion) {
        state.loadMotion(data.motion)
      }
      if (data.project) {
        set((s) => ({
          project: {
            ...s.project,
            name: data.project.name || s.project.name,
          },
        }))
      }
      return true
    } catch (error) {
      console.error('JSON 가져오기 실패:', error)
      return false
    }
  },

  // 저장 상태 업데이트
  markSaved: () => set((state) => ({
    project: { ...state.project, saved: true },
  })),

  markUnsaved: () => set((state) => ({
    project: { ...state.project, saved: false },
  })),

  // ==========================================
  // 전체 리셋
  // ==========================================
  reset: () => set(initialState),
}))

export default useStore
