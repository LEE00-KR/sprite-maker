import axios from 'axios'

const API_BASE_URL = '/api'

// Axios 인스턴스
const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 에러 핸들러
client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    throw error
  }
)

export const api = {
  // ==========================================
  // Characters
  // ==========================================
  getCharacters: () => client.get('/characters'),
  
  getCharacter: (id) => client.get(`/characters/${id}`),
  
  createCharacter: (data) => client.post('/characters', data),
  
  updateCharacter: (id, data) => client.put(`/characters/${id}`, data),
  
  deleteCharacter: (id) => client.delete(`/characters/${id}`),

  // ==========================================
  // Motions
  // ==========================================
  getMotions: (characterId) => client.get(`/characters/${characterId}/motions`),
  
  getMotion: (id) => client.get(`/motions/${id}`),
  
  createMotion: (characterId, data) => 
    client.post(`/characters/${characterId}/motions`, data),
  
  updateMotion: (id, data) => client.put(`/motions/${id}`, data),
  
  deleteMotion: (id) => client.delete(`/motions/${id}`),

  // ==========================================
  // Image Processing
  // ==========================================
  removeBackground: async (imageData, tolerance = 30, edgeSmoothing = 2) => {
    // Base64 이미지를 Blob으로 변환
    const base64Data = imageData.split(',')[1]
    const byteCharacters = atob(base64Data)
    const byteNumbers = new Array(byteCharacters.length)
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i)
    }
    const byteArray = new Uint8Array(byteNumbers)
    const blob = new Blob([byteArray], { type: 'image/png' })

    // FormData 생성
    const formData = new FormData()
    formData.append('image', blob, 'image.png')
    formData.append('tolerance', tolerance.toString())
    formData.append('edge_smoothing', edgeSmoothing.toString())

    return client.post('/image/remove-background', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  cutLayer: (imageData, mask) => 
    client.post('/image/cut-layer', { image_data: imageData, mask }),

  fillRegion: (imageData, mask, fillMethod = 'average') =>
    client.post('/image/fill', { image_data: imageData, mask, fill_method: fillMethod }),

  // ==========================================
  // Export
  // ==========================================
  exportSpritesheet: (data) => client.post('/export/spritesheet', data),
  
  exportGif: (data) => client.post('/export/gif', data),
  
  exportPngSequence: (data) => client.post('/export/png-sequence', data),
}

// ==========================================
// 유틸리티 함수
// ==========================================
export const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export const base64ToBlob = (base64, mimeType = 'image/png') => {
  const byteCharacters = atob(base64.split(',')[1])
  const byteNumbers = new Array(byteCharacters.length)
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i)
  }
  const byteArray = new Uint8Array(byteNumbers)
  return new Blob([byteArray], { type: mimeType })
}

export const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export const loadImage = (src) => {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

export default api
