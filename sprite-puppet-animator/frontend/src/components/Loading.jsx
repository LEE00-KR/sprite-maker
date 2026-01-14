import { useStore } from '../stores/useStore'

function Loading() {
  const { loadingMessage } = useStore()

  return (
    <div className="loading-overlay">
      <div className="loading-spinner" />
      {loadingMessage && (
        <p className="loading-text">{loadingMessage}</p>
      )}
    </div>
  )
}

export default Loading
