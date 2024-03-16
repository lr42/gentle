"""Detects AFK status based on mouse and keyboard activity"""


import time

# pylint: disable=import-error
import pynput
from PySide6.QtCore import QObject, QThread, QTimer, Slot, Signal


# pylint: disable=too-many-instance-attributes, too-few-public-methods
class AFKWorker(QObject):
    """
    Run a function when mouse or keyboard activity is detected, and
    optionally a different function after a timeout with no activty.
    """

    stopTimerSignal = Signal()

    def __init__(
        self,
        on_back_at_computer=None,
        on_afk=None,
        timeout=5,
        monitor_interval=100,
    ):
        """
        TODO TK Read PEP 257
        """

        super().__init__()

        self._is_afk = True

        self._on_back_at_computer = on_back_at_computer
        self._on_afk = on_afk
        self._monitor_interval = monitor_interval  # in milliseconds
        self._timeout = timeout

        self._last_input_time = time.time()

        self.kb_listener = pynput.keyboard.Listener(on_press=self._on_input)
        self.mouse_listener = pynput.mouse.Listener(
            on_move=self._on_input,
            on_click=self._on_input,
            on_scroll=self._on_input,
        )

        self._is_checking_for_afk = self._timeout >= 0

        if self._is_checking_for_afk:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._monitor_status)
            self.stopTimerSignal.connect(self._stop_worker)

    # pylint: disable=unused-argument
    def _on_input(self, *args):
        """Runs whenever mouse or keyboard activity is detected."""
        self._last_input_time = time.time()
        if not self._is_checking_for_afk:
            if self._on_back_at_computer is not None:
                self._on_back_at_computer()
        elif self._is_afk:
            self._is_afk = False
            if self._on_back_at_computer is not None:
                self._on_back_at_computer()

    @Slot()
    def _monitor_status(self):
        """Runs at a regular interval to check for AFK conditions"""
        elapsed_time = time.time() - self._last_input_time
        if not self._is_afk and elapsed_time > self._timeout:
            self._is_afk = True
            if self._on_afk is not None:
                self._on_afk()

    @Slot()
    def start_worker(self):
        """The slot to call when the thread running this worker is started."""
        if self._is_checking_for_afk:
            self._timer.start(self._monitor_interval)
        self.kb_listener.start()
        self.mouse_listener.start()

    @Slot()
    def _stop_worker(self):
        """The slot to call before shutting the thread down."""
        self._timer.stop()


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)

    afk_thread = QThread()
    afk_worker = AFKWorker(
        on_back_at_computer=lambda: print("Welcome back " + str(time.time())),
        on_afk=lambda: print("You are AFK " + str(time.time())),
    )
    afk_worker.moveToThread(afk_thread)
    afk_thread.started.connect(afk_worker.start_worker)
    afk_thread.start()

    input_thread = QThread()
    input_worker = AFKWorker(
        on_back_at_computer=lambda: print(".", end="", flush=True), timeout=-1
    )
    input_worker.moveToThread(input_thread)
    input_thread.started.connect(input_worker.start_worker)
    input_thread.start()

    mainWindow = QMainWindow()
    mainWindow.show()

    def cleanup():
        """
        Stop timers and threads, before exiting the application.  (Otherwise we
        get errors complaining that we didn't.)
        """
        afk_worker.stopTimerSignal.emit()
        afk_thread.quit()
        afk_thread.wait()

        input_worker.stopTimerSignal.emit()
        input_thread.quit()
        input_thread.wait()

    app.aboutToQuit.connect(cleanup)

    sys.exit(app.exec())
