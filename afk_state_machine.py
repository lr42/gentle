import logging
import afk_worker as aw
import stama.stama as sm


logger = logging.getLogger(__name__)


# ##############  Set up states

# fmt:off
at_computer         = sm.State("at computer")
away_from_keyboard  = sm.State("away from keyboard")
in_limbo            = sm.State("in limbo")

coming_back         = sm.ConditionalJunction(
                            at_computer,
                            "coming back to computer",
                      )


# ##############  Set up events

input_activity      = sm.Event("input activity detected")
timeout             = sm.Event("timeout")
# fmt:on


# ##############  Set up transitions

at_computer.transitions = {
    input_activity: at_computer,
    timeout: away_from_keyboard,
}

away_from_keyboard.transitions = {
    input_activity: in_limbo,
}

in_limbo.transitions = {
    input_activity: sm.Guard(
        lambda: True, coming_back
    ),  # TODO Fill in this guard condition
    timeout: away_from_keyboard,
}


# ##############  Start the state machine

afk_machine = sm.StateMachine(at_computer, "AFK SM")


# ##############  Main function, if not imported as a module

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    afk_machine.process_event(input_activity)
    afk_machine.process_event(timeout)
    afk_machine.process_event(input_activity)
    afk_machine.process_event(timeout)
    afk_machine.process_event(input_activity)
    afk_machine.process_event(input_activity)
    afk_machine.process_event(input_activity)
