import { useStore } from '../stores/useStore'
import { useEffect, useState } from 'react'

function PropertyPanel() {
  const { character, selection, updateLayer, updateJoint } = useStore()
  
  const [props, setProps] = useState({
    x: 0,
    y: 0,
    rotation: 0,
    scaleX: 100,
    scaleY: 100,
  })

  // 선택된 항목의 속성 로드
  useEffect(() => {
    if (selection.layers.length === 1) {
      const layer = character.layers.find((l) => l.id === selection.layers[0])
      if (layer) {
        setProps({
          x: layer.transform?.x || 0,
          y: layer.transform?.y || 0,
          rotation: layer.transform?.rotation || 0,
          scaleX: (layer.transform?.scaleX || 1) * 100,
          scaleY: (layer.transform?.scaleY || 1) * 100,
        })
      }
    } else if (selection.joints.length === 1) {
      const joint = character.joints.find((j) => j.id === selection.joints[0])
      if (joint) {
        setProps({
          x: joint.x || 0,
          y: joint.y || 0,
          rotation: 0,
          scaleX: 100,
          scaleY: 100,
        })
      }
    }
  }, [selection, character])

  const handleChange = (key, value) => {
    const numValue = parseFloat(value) || 0
    setProps((prev) => ({ ...prev, [key]: numValue }))

    // 레이어 업데이트
    if (selection.layers.length === 1) {
      const transform = {
        x: key === 'x' ? numValue : props.x,
        y: key === 'y' ? numValue : props.y,
        rotation: key === 'rotation' ? numValue : props.rotation,
        scaleX: key === 'scaleX' ? numValue / 100 : props.scaleX / 100,
        scaleY: key === 'scaleY' ? numValue / 100 : props.scaleY / 100,
      }
      updateLayer(selection.layers[0], { transform })
    }
    
    // 관절 업데이트
    if (selection.joints.length === 1) {
      updateJoint(selection.joints[0], {
        x: key === 'x' ? numValue : props.x,
        y: key === 'y' ? numValue : props.y,
      })
    }
  }

  const hasSelection = selection.layers.length > 0 || selection.joints.length > 0

  return (
    <div className="panel">
      <div className="panel__header">
        <h3 className="panel__title">⚙️ 속성</h3>
      </div>
      <div className="panel__body">
        {!hasSelection ? (
          <p className="text-muted" style={{ textAlign: 'center', padding: '20px' }}>
            선택된 항목이 없습니다.
          </p>
        ) : (
          <div className="property-group">
            <div className="form-group">
              <label>위치</label>
              <div style={{ display: 'flex', gap: 8 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 10 }}>X</label>
                  <input
                    type="number"
                    value={props.x}
                    onChange={(e) => handleChange('x', e.target.value)}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 10 }}>Y</label>
                  <input
                    type="number"
                    value={props.y}
                    onChange={(e) => handleChange('y', e.target.value)}
                  />
                </div>
              </div>
            </div>

            {selection.layers.length === 1 && (
              <>
                <div className="form-group">
                  <label>회전</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <input
                      type="number"
                      value={props.rotation}
                      onChange={(e) => handleChange('rotation', e.target.value)}
                      min={-360}
                      max={360}
                    />
                    <span className="text-muted">°</span>
                  </div>
                </div>

                <div className="form-group">
                  <label>크기</label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <div style={{ flex: 1 }}>
                      <label style={{ fontSize: 10 }}>W</label>
                      <input
                        type="number"
                        value={props.scaleX}
                        onChange={(e) => handleChange('scaleX', e.target.value)}
                      />
                    </div>
                    <div style={{ flex: 1 }}>
                      <label style={{ fontSize: 10 }}>H</label>
                      <input
                        type="number"
                        value={props.scaleY}
                        onChange={(e) => handleChange('scaleY', e.target.value)}
                      />
                    </div>
                    <span className="text-muted" style={{ alignSelf: 'flex-end', paddingBottom: 8 }}>%</span>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default PropertyPanel
