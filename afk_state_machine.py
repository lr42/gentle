import logging

from PySide6.QtCore import QObject, QThread, QTimer, Slot, Signal

import afk_worker as aw
import stama.stama as sm


logger = logging.getLogger(__name__)


class AFKStateMachine:
    """TK"""

    def __init__(self):
        # ##############  Set up states
        # fmt:off
        self._at_computer         = sm.State("at computer")
        self._away_from_keyboard  = sm.State("away from keyboard")
        self._in_limbo            = sm.State("in limbo")

        self._coming_back         = sm.ConditionalJunction(
                                    self._at_computer,
                                    "coming back to computer",
                              )

        # ##############  Set up events
        self.input_activity      = sm.Event("input activity detected")
        self.timeout             = sm.Event("timeout")
        # fmt:on

        # ##############  Set up transitions
        self._at_computer.transitions = {
            self.input_activity: self._at_computer,
            self.timeout: self._away_from_keyboard,
        }

        self._away_from_keyboard.transitions = {
            self.input_activity: self._in_limbo,
        }

        self._in_limbo.transitions = {
            self.input_activity: sm.Guard(
                lambda: True, self._coming_back
            ),  # TODO Fill in this guard condition
            self.timeout: self._away_from_keyboard,
        }

        # ##############  Start the state machine
        self._afk_machine = sm.StateMachine(self._at_computer, "AFK SM")

        # ##############  Start monitoring for input activity
        self._worker = aw.AFKWorker(
            timeout=-1,
            on_back_at_computer=lambda: self._afk_machine.process_event(
                self.input_activity
            ),
        )

        # TODO Is there a way to create and destroy the QThread automatically on object creation and destruction? ...
        #  Should I use a `with` statement to do something like this?
        #  (See https://stackoverflow.com/a/865272 for some info on
        #  this.)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start_worker)
        self._thread.start()

    # TODO process_event() is probably not necessary.
    def process_event(self, event):
        self._afk_machine.process_event(event)

    def cleanup(self):
        self._worker.stopTimerSignal.emit()
        self._thread.quit()
        self._thread.wait()


# ##############  Main function, if not imported as a module

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)

    mainWindow = QMainWindow()
    mainWindow.show()

    afk = AFKStateMachine()

    afk.process_event(afk.input_activity)
    afk.process_event(afk.timeout)
    afk.process_event(afk.input_activity)
    afk.process_event(afk.timeout)
    afk.process_event(afk.input_activity)
    afk.process_event(afk.input_activity)
    afk.process_event(afk.input_activity)

    app.aboutToQuit.connect(afk.cleanup)

    sys.exit(app.exec())
