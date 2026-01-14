import { useEffect, useCallback } from 'react'
import { useStore } from './stores/useStore'

// Components
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import Workspace from './components/Workspace'
import Timeline from './components/Timeline/Timeline'
import ExportModal from './components/Modal/ExportModal'
import CharacterModal from './components/Modal/CharacterModal'
import Toast from './components/Toast'
import Loading from './components/Loading'

function App() {
  const { isLoading, initApp, undo, redo, canUndo, canRedo } = useStore()

  useEffect(() => {
    initApp()
  }, [])

  // 키보드 단축키 처리
  const handleKeyDown = useCallback((e) => {
    // Ctrl+Z: Undo
    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
      e.preventDefault()
      if (canUndo()) {
        undo()
      }
    }
    // Ctrl+Y 또는 Ctrl+Shift+Z: Redo
    if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
      e.preventDefault()
      if (canRedo()) {
        redo()
      }
    }
  }, [undo, redo, canUndo, canRedo])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <div className="app">
      {/* 헤더 */}
      <Header />

      {/* 메인 영역 */}
      <main className="main">
        {/* 왼쪽 사이드바: 도구 모음 */}
        <Sidebar position="left" />

        {/* 중앙: 작업 영역 */}
        <Workspace />

        {/* 오른쪽 사이드바: 패널들 */}
        <Sidebar position="right" />
      </main>

      {/* 타임라인 */}
      <Timeline />

      {/* 모달들 */}
      <ExportModal />
      <CharacterModal />

      {/* 토스트 알림 */}
      <Toast />

      {/* 로딩 오버레이 */}
      {isLoading && <Loading />}
    </div>
  )
}

export default App
