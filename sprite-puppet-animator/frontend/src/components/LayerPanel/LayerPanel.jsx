import { useStore } from '../../stores/useStore'
import { Plus, Eye, EyeOff, Trash2 } from 'lucide-react'
import clsx from 'clsx'

function LayerPanel() {
  const { 
    character, 
    selection, 
    addLayer, 
    updateLayer, 
    removeLayer, 
    selectLayer,
    addToast 
  } = useStore()

  const handleAddLayer = () => {
    addLayer({ name: `레이어 ${character.layers.length + 1}` })
    addToast('레이어가 추가되었습니다.', 'success')
  }

  const handleToggleVisibility = (e, layerId, currentVisible) => {
    e.stopPropagation()
    updateLayer(layerId, { visible: !currentVisible })
  }

  const handleDelete = (e, layerId) => {
    e.stopPropagation()
    if (confirm('이 레이어를 삭제하시겠습니까?')) {
      removeLayer(layerId)
      addToast('레이어가 삭제되었습니다.', 'info')
    }
  }

  const handleSelect = (layerId, e) => {
    selectLayer(layerId, e.ctrlKey || e.metaKey)
  }

  return (
    <div className="panel">
      <div className="panel__header">
        <h3 className="panel__title">📑 레이어</h3>
        <div className="panel__actions">
          <button 
            className="btn btn--icon btn--sm" 
            onClick={handleAddLayer}
            title="레이어 추가"
          >
            <Plus size={16} />
          </button>
        </div>
      </div>
      <div className="panel__body">
        {character.layers.length === 0 ? (
          <p className="text-muted" style={{ textAlign: 'center', padding: '20px' }}>
            레이어가 없습니다.
          </p>
        ) : (
          <ul className="layer-list">
            {[...character.layers].reverse().map((layer) => (
              <li
                key={layer.id}
                className={clsx(
                  'layer-item',
                  selection.layers.includes(layer.id) && 'active'
                )}
                onClick={(e) => handleSelect(layer.id, e)}
              >
                <button
                  className={clsx(
                    'layer-item__visibility',
                    !layer.visible && 'hidden'
                  )}
                  onClick={(e) => handleToggleVisibility(e, layer.id, layer.visible)}
                  title={layer.visible ? '숨기기' : '표시'}
                >
                  {layer.visible ? <Eye size={14} /> : <EyeOff size={14} />}
                </button>
                
                <div 
                  className="layer-item__thumbnail"
                  style={{
                    backgroundImage: layer.imageData ? `url(${layer.imageData})` : 'none',
                    backgroundSize: 'contain',
                    backgroundPosition: 'center',
                    backgroundRepeat: 'no-repeat',
                  }}
                />
                
                <span className="layer-item__name">{layer.name}</span>
                
                <button
                  className="btn btn--icon btn--sm"
                  onClick={(e) => handleDelete(e, layer.id)}
                  title="삭제"
                  style={{ opacity: 0.5 }}
                >
                  <Trash2 size={14} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export default LayerPanel
