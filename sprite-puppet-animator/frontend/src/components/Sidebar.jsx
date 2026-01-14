import Toolbar from './Toolbar/Toolbar'
import LayerPanel from './LayerPanel/LayerPanel'
import SkeletonPanel from './SkeletonPanel'
import PropertyPanel from './PropertyPanel'

function Sidebar({ position }) {
  if (position === 'left') {
    return (
      <aside className="sidebar sidebar--left">
        <Toolbar />
      </aside>
    )
  }

  return (
    <aside className="sidebar sidebar--right">
      <LayerPanel />
      <SkeletonPanel />
      <PropertyPanel />
    </aside>
  )
}

export default Sidebar
