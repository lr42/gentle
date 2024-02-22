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
import breakscreen as bs


################  Config

# TODO Get these from a config file
short_break_max_spacing_time = 0.5 * 60  # in seconds
long_break_spacing_time = 25 * 60  # in seconds

length_of_short_break = 20  # in seconds
length_of_long_break = 5 * 60  # in seconds

length_of_early_notification_to_short_break = 25
length_of_early_notification_to_long_break = 2 * 60  # in seconds


################  States

waiting_for_short_break = sm.State("Waiting for a short break")
showing_short_break_early_notif = sm.State("Showing the short break early notification")
showing_short_break_late_notif = sm.State("Showing the short break late notification")
short_break_in_progress = sm.State("Short break in progress")
waiting_after_short_afk = sm.State("Waiting after AFK for short duration")

waiting_for_long_break = sm.State("Waiting for a long break")
showing_long_break_early_notif = sm.State("Showing the long break early notification")
showing_long_break_late_notif = sm.State("Showing the long break late notification")
long_break_in_progress = sm.State("long break in progress")
waiting_after_long_afk = sm.State("Waiting after AFK for long duration")

# TODO
test_for_next_break = sm.ConditionalJunction(waiting_for_long_break)

def has_short_break_before_long_break():
    secs_to_long_break = next_long_break_clock_time - time.time()
    if short_break_max_spacing_time < secs_to_long_break:
        return True
    return False

test_for_next_break.add_condition(has_short_break_before_long_break, waiting_for_short_break)


################  Events for the state machine

time_out = sm.Event("Time out")
break_started = sm.Event("Break started")
break_ended = sm.Event("Break ended")
afk_short_period_ended = sm.Event("Short AFK period ended")
afk_long_period_ended = sm.Event("Long AFK period ended")
returned_to_computer = sm.Event("User returned to computer")


################  Short break transitions

# fmt: off
waiting_for_short_break.transitions = {
    time_out:                showing_short_break_early_notif,
    afk_short_period_ended:  waiting_after_short_afk,
    returned_to_computer:    None,
}

showing_short_break_early_notif.transitions = {
    time_out:                   showing_short_break_late_notif,
    break_started:              short_break_in_progress,
    break_ended:                test_for_next_break,  # Skipping the break
    afk_short_period_ended:     waiting_after_short_afk,
    returned_to_computer:       None,
}

showing_short_break_late_notif.transitions = {
    break_started:              short_break_in_progress,
    break_ended:                test_for_next_break,  # Skipping the break
    afk_short_period_ended:     waiting_after_short_afk,
    returned_to_computer:       None,
}

short_break_in_progress.transitions = {
    break_ended:                test_for_next_break,
    afk_short_period_ended:     None,
    afk_long_period_ended:      None,  #TODO
    returned_to_computer:       None,  #TODO
}

waiting_after_short_afk.transitions = {
    afk_long_period_ended:      waiting_after_long_afk,
    returned_to_computer:       test_for_next_break,
}


################  Long break transitions

waiting_for_long_break.transitions = {
    time_out:                   showing_long_break_early_notif,
    afk_short_period_ended:     None,
    afk_long_period_ended:      waiting_after_long_afk,
    returned_to_computer:       None,
}

showing_long_break_early_notif.transitions = {
    time_out:                   showing_long_break_late_notif,
    break_started:              long_break_in_progress,
    break_ended:                test_for_next_break,  # Skipping the break
    afk_short_period_ended:     None,
    afk_long_period_ended:      waiting_after_long_afk,
    returned_to_computer:       None,
}

showing_long_break_late_notif.transitions = {
    break_started:              long_break_in_progress,
    break_ended:                test_for_next_break,  # Skipping the break
    afk_short_period_ended:     None,
    afk_long_period_ended:      waiting_after_long_afk,
    returned_to_computer:       None,
}

long_break_in_progress.transitions = {
    break_ended:                test_for_next_break,
    afk_short_period_ended:     None,
    afk_long_period_ended:      None,
    returned_to_computer:       None,  #TODO
}

waiting_after_long_afk.transitions = {
    returned_to_computer:       test_for_next_break,
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

    logger.info("%sm%ss to next short break", int(secs_to_short_break // 60), secs_to_short_break % 60)
    logger.info("%sm%ss to notification", int(secs_to_notification // 60), secs_to_notification % 60)

    #scheduler.enter(secs_to_notification, 1, lambda: machine.process_event(time_out))
    global_timer.singleShot(secs_to_notification * 1000, lambda: machine.process_event(time_out))

waiting_for_short_break.on_entry = waiting_for_short_break__on_entry


def early_notification_pulse():
    glowy.run_on_click = lambda: machine.process_event(break_started)

    glowy.show()

    # TODO Needs to come from configuration
    ending_fade_interval = glowy.steady_pulse_period / 2 / 1_000
    starting_fade_multiplier = 5
    starting_fade_interval = ending_fade_interval * starting_fade_multiplier

    my_iterable = gb.intervals_decreasing_over_total_time(
        starting_fade_multiplier,
        ending_fade_interval,
        # This needs to be part of the GlowBox object.
        length_of_early_notification_to_short_break,
        # TODO These need to be in the main program
        glowy.color_main,
        glowy.color_early,
    )

    glowy.transition_color_over_iterable(my_iterable, lambda: machine.process_event(time_out))

showing_short_break_early_notif.on_entry = early_notification_pulse


def showing_short_break_late_notif__on_entry():
    glowy.run_on_click = lambda: machine.process_event(break_started)

    my_iterable = gb.steady_pulse(glowy.steady_pulse_period, glowy.color_main, glowy.color_late)
    glowy.transition_color_over_iterable(my_iterable, None)

showing_short_break_late_notif.on_entry = showing_short_break_late_notif__on_entry


def show_short_break_screen():
    shorty.showFullScreen()

short_break_in_progress.on_entry = show_short_break_screen


def hide_short_break_screen():
    shorty.hide()

short_break_in_progress.on_exit = hide_short_break_screen


################  Long break state actions

################  Main
if __name__ == '__main__':

    ################  Logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    logger.info("Logging initialized")

    ################  Set up concurrent activities
    #threading.Thread(target=scheduler_thread, daemon=True).start()
    global_timer = QTimer()

    next_long_break_clock_time = time.time() + long_break_spacing_time

    ################  Set up QT
    app = QApplication(sys.argv)

    glowy = gb.GlowBox()

    shorty = bs.ShortBreakScreen(5, lambda: machine.process_event(break_ended))

    ################  Add tray icon
    tray_icon = QSystemTrayIcon(QIcon('6138023.png'))

    tray_menu = QMenu()
    action = QAction('Exit', tray_icon)
    action.triggered.connect(app.quit)
    tray_menu.addAction(action)
    tray_icon.setContextMenu(tray_menu)

    tray_icon.show()

    ################  Start state machine
    machine = sm.StateMachine(waiting_for_short_break)

    ################  Exit on QT app close
    sys.exit(app.exec())

