"""Detects AFK status based on mouse and keyboard activity."""


import time

# pylint: disable=import-error
import pynput
from PySide6.QtCore import QObject, QThread, QTimer, Slot, Signal


# pylint: disable=too-many-instance-attributes, too-few-public-methods
class AFKWorker(QObject):
    """
    TODO TK
    """

    stopTimerSignal = Signal()

    afk_signal = Signal(float)
    at_computer_signal = Signal(float)
    in_limbo_signal = Signal()
    leaving_limbo_signal = Signal()

    _AT_COMPUTER = "at computer"  # pylint: disable=invalid-name
    _AFK = "away from keyboard"  # pylint: disable=invalid-name
    _IN_LIMBO = "in limbo"  # pylint: disable=invalid-name

    def __init__(
        self,
        input_timeout=30,
        limbo_timeout=5,  # TODO 2 separate timeouts: to AFK and to at compy.
        #  Limbo should be quick to go to "at computer" but slow to go back to
        #  "afk" status.
        monitor_interval=100,
    ):
        """
        TODO TK Read PEP 257
        """

        super().__init__()

        self._status = self._AT_COMPUTER

        self._monitor_interval = monitor_interval  # in milliseconds
        self._input_timeout = input_timeout
        self._limbo_timeout = limbo_timeout

        self._last_input_time = time.time()
        self._entered_limbo_time = 0

        self.kb_listener = pynput.keyboard.Listener(on_press=self._on_input)
        self.mouse_listener = pynput.mouse.Listener(
            on_move=self._on_input,
            on_click=self._on_input,
            on_scroll=self._on_input,
        )

        self._is_checking_for_afk = self._input_timeout > 0
        self._is_using_limbo_state = self._limbo_timeout > 0

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
                    self.in_limbo_signal.emit()
                elif self._status == self._IN_LIMBO:
                    elapsed_limbo_time = time.time() - self._entered_limbo_time
                    if elapsed_limbo_time > self._limbo_timeout:
                        self._status = self._AT_COMPUTER
                        self.leaving_limbo_signal.emit()
                        self.at_computer_signal.emit(self._entered_limbo_time)
            else:
                if self._status == self._AFK:
                    self._status = self._AT_COMPUTER
                    self.at_computer_signal.emit(time.time())
        else:
            self.at_computer_signal.emit(time.time())

    @Slot()
    def _monitor_status(self):
        """Runs at a regular interval to check for AFK conditions"""
        elapsed_input_time = time.time() - self._last_input_time

        if (
            self._status == self._IN_LIMBO
            and elapsed_input_time > self._limbo_timeout
        ):
            self._status = self._AFK
            self.leaving_limbo_signal.emit()
        elif (
            self._status == self._AT_COMPUTER
            and elapsed_input_time > self._input_timeout
        ):
            self._status = self._AFK
            self.afk_signal.emit(self._last_input_time)

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
    afk_worker = AFKWorker(input_timeout=10)

    afk_worker.at_computer_signal.connect(
        lambda t: print(
            "Back since: "
            + time.strftime("%H:%M:%S", time.localtime(t))
            + " -- Now: "
            + time.strftime("%H:%M:%S")
        )
    )
    afk_worker.afk_signal.connect(
        lambda t: print(
            "AFK since: "
            + time.strftime("%H:%M:%S", time.localtime(t))
            + " -- Now: "
            + time.strftime("%H:%M:%S")
        )
    )
    afk_worker.leaving_limbo_signal.connect(
        lambda: print("Leaving limbo: " + time.strftime("%H:%M:%S"))
    )
    afk_worker.in_limbo_signal.connect(
        lambda: print("Entering limbo: " + time.strftime("%H:%M:%S"))
    )

    afk_worker.moveToThread(afk_thread)
    afk_thread.started.connect(afk_worker.start_worker)
    afk_thread.start()

    input_thread = QThread()
    input_worker = AFKWorker(input_timeout=0)

    input_worker.at_computer_signal.connect(
        lambda: print(".", end="", flush=True)
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
