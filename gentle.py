import math
import sched
import time
import threading
import logging
import sys

from PySide6.QtCore import (
    Qt,
    QPropertyAnimation,
    Property,
    QEasingCurve,
    QTimer,
    QTime,
)
from PySide6.QtGui import QAction, QColor, QPalette, QScreen, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QSizeGrip,
    QPushButton,
    QMenu,
    QVBoxLayout,
    QLabel,
    QSystemTrayIcon,
)

import stama.stama as sm
import glowbox as gb


################  Config
# TODO Get these from a config file
short_break_max_spacing_time = 0.5 * 60  # in seconds
long_break_spacing_time = 25 * 60  # in seconds

length_of_short_break = 20  # in seconds
length_of_long_break = 5 * 60  # in seconds

length_of_early_notification_to_short_break = 20
length_of_early_notification_to_long_break = 2 * 60  # in seconds


################  States
waiting_for_short_break = sm.State()
showing_short_break_notif = sm.State()
short_break_in_progress = sm.State()
waiting_after_short_afk = sm.State()

waiting_for_long_break = sm.State()
showing_long_break_notif = sm.State()
long_break_in_progress = sm.State()
waiting_after_long_afk = sm.State()

# TODO
test_for_next_break = sm.ConditionalJunction(waiting_for_long_break)


################  Events for the state machine
time_out = sm.Event()
break_started = sm.Event()
break_ended = sm.Event()
afk_short_period_ended = sm.Event()
afk_long_period_ended = sm.Event()
returned_to_computer = sm.Event()


################  Transitions
# fmt: off
waiting_for_short_break.transitions = {
    time_out:                showing_short_break_notif,
    afk_short_period_ended:  waiting_after_short_afk,
    returned_to_computer:    None,
}

showing_short_break_notif.transitions = {
    break_started:           short_break_in_progress,
    break_ended:             test_for_next_break,  # Skipping the break
    afk_short_period_ended:  waiting_after_short_afk,
    returned_to_computer:    None,
}

short_break_in_progress.transitions = {
    break_ended:             test_for_next_break,
    afk_short_period_ended:  None,
    afk_long_period_ended:   None,  #TODO
    returned_to_computer:    None,  #TODO
}

waiting_after_short_afk.transitions = {
    afk_long_period_ended:   waiting_after_long_afk,
    returned_to_computer:    test_for_next_break,
}


waiting_for_long_break.transitions = {
    time_out:                showing_long_break_notif,
    afk_short_period_ended:  None,
    afk_long_period_ended:   waiting_after_long_afk,
    returned_to_computer:    None,
}

showing_long_break_notif.transitions = {
    break_started:           long_break_in_progress,
    break_ended:             test_for_next_break,  # Skipping the break
    afk_short_period_ended:  None,
    afk_long_period_ended:   waiting_after_long_afk,
    returned_to_computer:    None,
}

long_break_in_progress.transitions = {
    break_ended:             test_for_next_break,
    afk_short_period_ended:  None,
    afk_long_period_ended:   None,
    returned_to_computer:    None,  #TODO
}

waiting_after_long_afk.transitions = {
    returned_to_computer:    test_for_next_break,
}
# fmt:on


################  Short break state actions
def waiting_for_short_break__on_entry():
    secs_to_long_break = next_long_break_clock_time - time.time()
    num_segments_to_long_break = math.ceil(
        (secs_to_long_break + length_of_short_break)
        / (length_of_short_break + short_break_max_spacing_time)
    )
    num_short_breaks_to_long_break = num_segments_to_long_break - 1
    total_short_break_secs_to_long_break = (
        num_short_breaks_to_long_break * length_of_short_break
    )
    working_secs_to_long_break = (
        secs_to_long_break - total_short_break_secs_to_long_break
    )
    secs_to_short_break = (
        working_secs_to_long_break / num_segments_to_long_break
    )
    secs_to_notification = (
        secs_to_short_break - length_of_early_notification_to_short_break
    )

    print(secs_to_short_break / 60)
    print(secs_to_notification)

    scheduler.enter(secs_to_notification, 1, lambda: machine.process_event(time_out))


waiting_for_short_break.on_entry = waiting_for_short_break__on_entry


def waiting_for_short_break__on_exit():
    pass


def showing_short_break_notif__on_entry():
    print("Donkeys live a very long time")

showing_short_break_notif.on_entry = showing_short_break_notif__on_entry

def showing_short_break_notif__on_exit():
    pass


def short_break_in_progress__on_entry():
    pass


def short_break_in_progress__on_exit():
    pass


def waiting_after_short_afk__on_entry():
    pass


def waiting_after_short_afk__on_exit():
    pass


def waiting_for_long_break__on_entry():
    pass


def waiting_for_long_break__on_exit():
    pass


def showing_long_break_notif__on_entry():
    pass


def showing_long_break_notif__on_exit():
    pass


################  Long break state actions
def long_break_in_progress__on_entry():
    pass


def long_break_in_progress__on_exit():
    pass


def waiting_after_long_afk__on_entry():
    pass


def waiting_after_long_afk__on_exit():
    pass


################  Threads
scheduler = sched.scheduler(time.monotonic, time.sleep)
scheduler_lock = threading.Lock()
def scheduler_thread():
    while True:
        with scheduler_lock:
            time_to_next_event = scheduler.run(blocking=False)
        if time_to_next_event is None:
            time.sleep(1)
        else:
            time.sleep(time_to_next_event)


################  Main
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.info("Logging initialized")

threading.Thread(target=scheduler_thread, daemon=True).start()

next_long_break_clock_time = time.time() + long_break_spacing_time
machine = sm.StateMachine(waiting_for_short_break)

app = QApplication(sys.argv)

tray_icon = QSystemTrayIcon(QIcon('6138023.png'))

tray_menu = QMenu()
action = QAction('Exit', tray_icon)
action.triggered.connect(app.quit)
tray_menu.addAction(action)
tray_icon.setContextMenu(tray_menu)

tray_icon.show()

glowy = gb.GlowBox()
print("Showing glowy")
glowy.show()

starting_fade_multiplier = 5
total_time_for_transition = 120
my_iterable = gb.intervals_decreasing_over_total_time(
    starting_fade_multiplier,
    # This needs to be part of the GlowBox object.
    glowy.steady_pulse_period / 2 / 1_000,
    total_time_for_transition,
    glowy.color_main,
    glowy.color_early,
)

glowy.transition_color_over_iterable(my_iterable, lambda: print("DONE!!!!!!!"))

sys.exit(app.exec())
