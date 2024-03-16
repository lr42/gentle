import logging
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

    def process_event(self, event):
        self._afk_machine.process_event(event)


# ##############  Main function, if not imported as a module

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    afk = AFKStateMachine()

    afk.process_event(afk.input_activity)
    afk.process_event(afk.timeout)
    afk.process_event(afk.input_activity)
    afk.process_event(afk.timeout)
    afk.process_event(afk.input_activity)
    afk.process_event(afk.input_activity)
    afk.process_event(afk.input_activity)
