"""Detects AFK status based on mouse and keyboard activity."""


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

        self._AT_COMPUTER = "at computer"
        self._AFK = "away from keyboard"
        self._IN_LIMBO = "in limbo"

        self._status = self._AT_COMPUTER

        self._on_back_at_computer = on_back_at_computer
        self._on_afk = on_afk
        self._monitor_interval = monitor_interval  # in milliseconds
        self._input_timeout = timeout
        self._limbo_timeout = 10

        self._last_input_time = time.time()
        self._entered_limbo_time = 0

        self.kb_listener = pynput.keyboard.Listener(on_press=self._on_input)
        self.mouse_listener = pynput.mouse.Listener(
            on_move=self._on_input,
            on_click=self._on_input,
            on_scroll=self._on_input,
        )

        self._is_checking_for_afk = self._input_timeout > 0
        self._is_using_limbo_state = self._is_checking_for_afk

        if self._is_checking_for_afk:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._monitor_status)
            self.stopTimerSignal.connect(self._stop_worker)

    # pylint: disable=unused-argument
    def _on_input(self, *args):
        """Runs whenever mouse or keyboard activity is detected."""
        self._last_input_time = time.time()

        if self._is_checking_for_afk:
            if self._is_using_limbo_state:
                if self._status == self._AFK:
                    self._status = self._IN_LIMBO
                    self._entered_limbo_time = time.time()
                    # TODO Emit entering_limbo signal
                    print("Entering limbo")
                elif self._status == self._IN_LIMBO:
                    elapsed_limbo_time = time.time() - self._entered_limbo_time
                    if elapsed_limbo_time > self._limbo_timeout:
                        self._status = self._AT_COMPUTER
                        if self._on_back_at_computer is not None:
                            self._on_back_at_computer()
            else:
                if self._status == self._AFK:
                    self._status = self._AT_COMPUTER
                    if self._on_back_at_computer is not None:
                        self._on_back_at_computer()
        else:
            if self._on_back_at_computer is not None:
                self._on_back_at_computer()

    @Slot()
    def _monitor_status(self):
        """Runs at a regular interval to check for AFK conditions"""
        elapsed_input_time = time.time() - self._last_input_time
        # elapsed_limbo_time = time.time() - self._last_limbo_time

        if (
            self._status == self._IN_LIMBO
            and elapsed_input_time > self._limbo_timeout
        ):
            self._status = self._AFK
            # TODO Emit leaving_limbo signal
            print("Leaving limbo")
        elif (
            self._status == self._AT_COMPUTER
            and elapsed_input_time > self._input_timeout
        ):
            self._status = self._AFK
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
