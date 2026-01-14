import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'

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
  addLayer: (layer) => set((state) => ({
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
  })),

  updateLayer: (layerId, updates) => set((state) => ({
    character: {
      ...state.character,
      layers: state.character.layers.map((layer) =>
        layer.id === layerId ? { ...layer, ...updates } : layer
      ),
    },
  })),

  removeLayer: (layerId) => set((state) => ({
    character: {
      ...state.character,
      layers: state.character.layers.filter((l) => l.id !== layerId),
    },
    selection: {
      ...state.selection,
      layers: state.selection.layers.filter((id) => id !== layerId),
    },
  })),

  reorderLayers: (newOrder) => set((state) => ({
    character: {
      ...state.character,
      layers: newOrder,
    },
  })),

  // ==========================================
  // 관절 관리
  // ==========================================
  addJoint: (joint) => set((state) => {
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
  }),

  updateJoint: (jointId, updates) => set((state) => ({
    character: {
      ...state.character,
      joints: state.character.joints.map((joint) =>
        joint.id === jointId ? { ...joint, ...updates } : joint
      ),
    },
  })),

  removeJoint: (jointId) => set((state) => ({
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
  })),

  // ==========================================
  // 뼈대 관리
  // ==========================================
  addBone: (startJointId, endJointId) => set((state) => {
    // 이미 존재하는지 확인
    const exists = state.character.bones.some(
      (b) =>
        (b.startJointId === startJointId && b.endJointId === endJointId) ||
        (b.startJointId === endJointId && b.endJointId === startJointId)
    )
    if (exists) return state

    const newBone = {
      id: uuidv4(),
      name: `뼈대 ${state.character.bones.length + 1}`,
      startJointId,
      endJointId,
    }
    return {
      character: {
        ...state.character,
        bones: [...state.character.bones, newBone],
      },
    }
  }),

  removeBone: (boneId) => set((state) => ({
    character: {
      ...state.character,
      bones: state.character.bones.filter((b) => b.id !== boneId),
    },
  })),

  // ==========================================
  // 키프레임 관리
  // ==========================================
  addKeyframe: (jointId, frameNumber, props) => set((state) => {
    const existingIndex = state.currentMotion.keyframes.findIndex(
      (kf) => kf.jointId === jointId && kf.frameNumber === frameNumber
    )

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

    return {
      currentMotion: {
        ...state.currentMotion,
        keyframes: newKeyframes,
      },
    }
  }),

  removeKeyframe: (keyframeId) => set((state) => ({
    currentMotion: {
      ...state.currentMotion,
      keyframes: state.currentMotion.keyframes.filter(
        (kf) => kf.id !== keyframeId
      ),
    },
  })),

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
  // 전체 리셋
  // ==========================================
  reset: () => set(initialState),
}))

export default useStore
