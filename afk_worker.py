"""Detects AFK status based on mouse and keyboard activity."""

# TODO Test for weird timings and raise a warning if one is found.


import time
from typing import List, Optional
import logging

# pylint: disable=import-error
import pynput
from PySide6.QtCore import QObject, QThread, QTimer, Slot, Signal


logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes, too-few-public-methods
class AFKWorker(QObject):
    """
    Emit signals on key/mouse activity, and "away from keyboard" timeouts.
    """

    stopTimerSignal = Signal()

    afk_signal = Signal(float)
    at_computer_signal = Signal(float)
    in_limbo_signal = Signal()
    leaving_limbo_signal = Signal()
    scheduled_signal = Signal(float)

    _AT_COMPUTER = "at computer"  # pylint: disable=invalid-name
    _AFK = "away from keyboard"  # pylint: disable=invalid-name
    _IN_LIMBO = "in limbo"  # pylint: disable=invalid-name

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        input_timeout: float = 30,
        limbo_timeout_to_back: float = 5,
        limbo_timeout_to_afk: Optional[float] = None,
        limbo_timeout_to_afk_multiplier: float = 3,
        scheduled_timeouts: Optional[List[float]] = None,
        monitor_interval: float = 100,
    ):
        """
        Constructs the AFKWorker object.

        Args:
            input_timeout: The amount of time (in seconds) before going to an
                "AFK" status.

            limbo_timeout_to_back: Time (in seconds) after which any input in a
                "limbo" status will transition to a "at computer" status.

            limbo_timeout_to_afk: Time (in seconds) after which no activity in
                a "limbo" status will transition back to an "AFK" status.  This
                will override any `limbo_timeout_to_afk_multiplier` value.

            limbo_timeout_to_afk_multiplier: The amount to multiply the
                `limbo_timeout_to_back` value to get the `limbo_timeout_to_afk`
                value.  Only applicable if no 'limbo_timeout_to_afk` parameter
                is passed.

            scheduled_timeouts: A list of floats, which will emit a signal with
                the value of the float when that amount of time (in seconds)
                into an "AFK" state.  This value returned by this signal can be
                analyzed to run a specific action.  The signals raised by this
                process can be emitted before the AFKWorker object officially
                enters the "AFK" state.

            monitor_interval: How frequently (in milliseconds) to monitor and
                update the status.
        """

        super().__init__()

        self._status = self._AT_COMPUTER

        self._monitor_interval = monitor_interval  # in milliseconds
        self._input_timeout = input_timeout
        self._limbo_timeout_to_back = limbo_timeout_to_back
        if limbo_timeout_to_afk is not None:
            self._limbo_timeout_to_afk = limbo_timeout_to_afk
        else:
            self._limbo_timeout_to_afk = (
                limbo_timeout_to_back * limbo_timeout_to_afk_multiplier
            )

        if scheduled_timeouts is not None:
            self._scheduled_timeouts = scheduled_timeouts
            self._scheduled_timeouts.sort()
        else:
            self._scheduled_timeouts = []
        self._scheduled_current_index = 0

        self._last_input_time = time.time()
        self._entered_limbo_time = 0

        self.kb_listener = pynput.keyboard.Listener(on_press=self._on_input)
        self.mouse_listener = pynput.mouse.Listener(
            on_move=self._on_input,
            on_click=self._on_input,
            on_scroll=self._on_input,
        )

        self._is_only_monitoring_input = (
            self._input_timeout <= 0 and scheduled_timeouts is None
        )
        self._is_using_limbo_state = self._limbo_timeout_to_back > 0

        if not self._is_only_monitoring_input:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._monitor_status)
            self.stopTimerSignal.connect(self._stop_worker)

    # pylint: disable=unused-argument
    def _on_input(self, *args):
        """Runs whenever mouse or keyboard activity is detected."""
        self._last_input_time = time.time()

        if not self._is_only_monitoring_input:
            if self._is_using_limbo_state:
                if self._status == self._AFK:
                    self._status = self._IN_LIMBO
                    self._entered_limbo_time = time.time()
                    logger.debug("Emitting 'in limbo'")
                    self.in_limbo_signal.emit()
                elif self._status == self._IN_LIMBO:
                    elapsed_limbo_time = time.time() - self._entered_limbo_time
                    if elapsed_limbo_time > self._limbo_timeout_to_back:
                        self._status = self._AT_COMPUTER
                        logger.debug("Emitting 'leaving limbo'")
                        self.leaving_limbo_signal.emit()
                        logger.debug("Emitting 'at computer'")
                        self.at_computer_signal.emit(self._entered_limbo_time)
            else:
                if self._status == self._AFK:
                    self._status = self._AT_COMPUTER
                    logger.debug("Emitting 'at computer'")
                    self.at_computer_signal.emit(time.time())
        else:
            logger.debug("Emitting 'at computer'")
            self.at_computer_signal.emit(time.time())

        if self._status == self._AT_COMPUTER:
            self._scheduled_current_index = 0

    @Slot()
    def _monitor_status(self):
        """Runs at a regular interval to check for AFK conditions"""
        elapsed_input_time = time.time() - self._last_input_time

        if (
            self._status == self._IN_LIMBO
            and elapsed_input_time > self._limbo_timeout_to_afk
        ):
            self._status = self._AFK
            logger.debug("Emitting 'leaving computer'")
            self.leaving_limbo_signal.emit()
        elif (
            self._status == self._AT_COMPUTER
            and elapsed_input_time > self._input_timeout
        ):
            self._status = self._AFK
            logger.debug("Emitting 'AFK'")
            self.afk_signal.emit(self._last_input_time)

        while True:
            if self._scheduled_current_index >= len(self._scheduled_timeouts):
                break
            current_scheduled_time = self._scheduled_timeouts[
                self._scheduled_current_index
            ]
            if elapsed_input_time > current_scheduled_time:
                logger.debug("Emitting 'scheduled event'")
                self.scheduled_signal.emit(current_scheduled_time)
                self._scheduled_current_index += 1
            else:
                break

    @Slot()
    def start_worker(self):
        """The slot to call when the thread running this worker is started."""
        if not self._is_only_monitoring_input:
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

    # ##############  Set up thread that tracks AFK status
    scheduled_events = {
        5: lambda: print("Nothing in a bit: " + time.strftime("%H:%M:%S")),
        15: lambda: print("Nothing for a while: " + time.strftime("%H:%M:%S")),
    }

    afk_thread = QThread()
    afk_worker = AFKWorker(
        input_timeout=10,
        scheduled_timeouts=list(scheduled_events.keys()),
    )

    afk_worker.scheduled_signal.connect(lambda t: scheduled_events[t]())

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

    # ##############  Set up thread that ticks on any input
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
