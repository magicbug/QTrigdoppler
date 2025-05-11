from PySide6.QtCore import QObject, Signal

class WebApiGuiProxy(QObject):
    select_satellite = Signal(str)
    select_transponder = Signal(str)
    set_subtone = Signal(str)
    set_rx_offset = Signal(int)
    start_tracking = Signal()
    stop_tracking = Signal()
    # Add more signals as needed for other GUI/timer actions 