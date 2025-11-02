from PyQt6.QtWidgets import QApplication
from types import SimpleNamespace
import sys

# Minimal smoke test: import DashboardTab and instantiate in offscreen mode
try:
    app = QApplication.instance() or QApplication([])
    user = SimpleNamespace(username='smoke', role='admin')
    from ui.tabs.dashboard import DashboardTab
    w = DashboardTab(user)
    w.show()
    print('SMOKE_OK')
    # Clean up
    w.deleteLater()
    app.quit()
    sys.exit(0)
except Exception as e:
    print('SMOKE_FAIL', e)
    sys.exit(2)
