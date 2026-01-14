import { useStore } from '../stores/useStore'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react'

function Toast() {
  const { toasts, removeToast } = useStore()

  const getIcon = (type) => {
    switch (type) {
      case 'success':
        return <CheckCircle size={20} color="var(--color-success)" />
      case 'error':
        return <AlertCircle size={20} color="var(--color-error)" />
      case 'warning':
        return <AlertTriangle size={20} color="var(--color-warning)" />
      default:
        return <Info size={20} color="var(--color-primary)" />
    }
  }

  if (toasts.length === 0) return null

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast--${toast.type}`}>
          {getIcon(toast.type)}
          <span style={{ flex: 1 }}>{toast.message}</span>
          <button
            onClick={() => removeToast(toast.id)}
            style={{ 
              background: 'none', 
              border: 'none', 
              cursor: 'pointer',
              opacity: 0.5,
              color: 'var(--text-primary)'
            }}
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  )
}

export default Toast
