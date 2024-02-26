import math
import sched
import time
import threading
import logging
from logging.handlers import SocketHandler
import sys
import datetime

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
#short_break_max_spacing_time = 20  # in seconds
#long_break_spacing_time = 0.5 * 60  # in seconds
#
#length_of_short_break = 5  # in seconds
#length_of_long_break = 5 #* 60  # in seconds
#
#length_of_early_notification_to_short_break = 10  # in seconds
#length_of_early_notification_to_long_break = 10  # in seconds

short_break_max_spacing_time = 20 * 60  # in seconds
long_break_spacing_time = 25 * 60  # in seconds

length_of_short_break = 30  # in seconds
length_of_long_break = 5 * 60  # in seconds

length_of_early_notification_to_short_break = 30  # in seconds
length_of_early_notification_to_long_break = 2 * 60  # in seconds

steady_pulse_period = 1_000

# TODO Maybe use separate colors for short and long early and late notifications?
color_short = "chartreuse"
color_long = "deepskyblue"
color_early = "white"
color_late = "yellow"


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
long_break_finished = sm.State("long break finished")
waiting_after_long_afk = sm.State("Waiting after AFK for long duration")

# TODO
test_for_next_break = sm.ConditionalJunction(waiting_for_long_break)

def has_short_break_before_long_break():
    global next_long_break_clock_time
    logger.info("Next long break at:  %s", datetime.datetime.fromtimestamp(next_long_break_clock_time).strftime("%H:%M:%S"))
    if time.time() > next_long_break_clock_time:
        next_long_break_clock_time = time.time() + long_break_spacing_time
        logger.info("Next long break reset to:  %s", datetime.datetime.fromtimestamp(next_long_break_clock_time).strftime("%H:%M:%S"))
    secs_to_long_break = next_long_break_clock_time - time.time()
    if short_break_max_spacing_time < secs_to_long_break:
        logger.debug("has_short_break_before_long_break returning True: short_break_max_spacing_time (%s) < secs_to_long_break (%s)", short_break_max_spacing_time, secs_to_long_break)
        return True
    logger.debug("has_short_break_before_long_break returning False: short_break_max_spacing_time (%s) >= secs_to_long_break (%s)", short_break_max_spacing_time, secs_to_long_break)
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
    time_out:                   long_break_finished,
    break_ended:                test_for_next_break,  # Skipping the break
    afk_short_period_ended:     None,
    afk_long_period_ended:      None,
    returned_to_computer:       None,  #TODO
}

long_break_finished.transitions = {
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

def set_timer_for_short_break():
    secs_to_long_break = next_long_break_clock_time - time.time()
    logger.debug("secs_to_long_break:  %s", secs_to_long_break)

    num_segments_to_long_break = math.ceil(
        (secs_to_long_break + length_of_short_break)
        / (length_of_short_break + short_break_max_spacing_time)
    )
    logger.debug("num_segments_to_long_break:  %s", num_segments_to_long_break)

    num_short_breaks_to_long_break = num_segments_to_long_break - 1
    logger.debug("num_short_breaks_to_long_break:  %s", num_short_breaks_to_long_break)

    total_short_break_secs_to_long_break = (
        num_short_breaks_to_long_break * length_of_short_break
    )
    logger.debug("total_short_break_secs_to_long_break:  %s", total_short_break_secs_to_long_break)

    working_secs_to_long_break = (
        secs_to_long_break - total_short_break_secs_to_long_break
    )
    logger.debug("working_secs_to_long_break:  %s", working_secs_to_long_break)

    secs_to_short_break = (
        working_secs_to_long_break / num_segments_to_long_break
    )
    logger.debug("secs_to_short_break:  %s", secs_to_short_break)

    secs_to_notification = (
        secs_to_short_break - length_of_early_notification_to_short_break
    )
    logger.debug("secs_to_notification:  %s", secs_to_notification)

    secs_to_notification = max(secs_to_notification, 0)

    logger.info("%sm%ss to next short break", int(secs_to_short_break // 60), secs_to_short_break % 60)
    logger.info("%sm%ss to notification", int(secs_to_notification // 60), secs_to_notification % 60)

    global_timer.singleShot(secs_to_notification * 1000, lambda: machine.process_event(time_out))

waiting_for_short_break.on_entry = set_timer_for_short_break


def clear_time_out_timer():
    global_timer.stop()

waiting_for_short_break.on_exit = clear_time_out_timer


def short_early_notification_pulse():
    glowy.set_main_color(color_short)
    glowy.run_on_click = lambda: machine.process_event(break_started)

    # TODO Should this include the color to show it as?
    glowy.show()

    # TODO Needs to come from configuration
    ending_fade_interval = steady_pulse_period / 2 / 1_000
    logger.debug("ending_fade_interval: %s", ending_fade_interval)
    starting_fade_multiplier = 5
    starting_fade_interval = ending_fade_interval * starting_fade_multiplier

    my_iterable = gb.intervals_decreasing_over_total_time(
        starting_fade_multiplier,
        ending_fade_interval,
        # This needs to be part of the GlowBox object.
        length_of_early_notification_to_short_break,
        # TODO These need to be in the main program
        color_short,
        color_early,
    )

    glowy.transition_color_over_iterable(my_iterable, lambda: machine.process_event(time_out))

showing_short_break_early_notif.on_entry = short_early_notification_pulse


def short_late_notification_pulse():
    glowy.set_main_color(color_short)
    glowy.run_on_click = lambda: machine.process_event(break_started)

    my_iterable = gb.steady_pulse(steady_pulse_period / 2, color_short, color_late)
    glowy.transition_color_over_iterable(my_iterable, None)

showing_short_break_late_notif.on_entry = short_late_notification_pulse


def show_short_break_screen():
    shorty.showFullScreen()

short_break_in_progress.on_entry = show_short_break_screen


def hide_short_break_screen():
    shorty.hide()

short_break_in_progress.on_exit = hide_short_break_screen


################  Long break state actions

def set_timer_for_long_break():
    secs_to_long_break = next_long_break_clock_time - time.time()
    secs_to_notification = (
        secs_to_long_break - length_of_early_notification_to_long_break
    )

    secs_to_notification = max(secs_to_notification, 0)

    logger.info("%sm%ss to next long break", int(secs_to_long_break // 60), secs_to_long_break % 60)
    logger.info("%sm%ss to notification", int(secs_to_notification // 60), secs_to_notification % 60)

    global_timer.singleShot(secs_to_notification * 1000, lambda: machine.process_event(time_out))

waiting_for_long_break.on_entry = set_timer_for_long_break

waiting_for_long_break.on_exit = clear_time_out_timer


def long_early_notification_pulse():
    # TODO Should this be a setter?
    glowy.set_main_color(color_long)
    glowy.run_on_click = lambda: machine.process_event(break_started)

    glowy.show()

    # TODO Needs to come from configuration
    ending_fade_interval = steady_pulse_period / 2 / 1_000
    logger.debug("ending_fade_interval: %s", ending_fade_interval)
    starting_fade_multiplier = 5
    starting_fade_interval = ending_fade_interval * starting_fade_multiplier

    my_iterable = gb.intervals_decreasing_over_total_time(
        starting_fade_multiplier,
        ending_fade_interval,
        # This needs to be part of the GlowBox object.
        length_of_early_notification_to_long_break,
        # TODO These need to be in the main program
        color_long,
        color_early,
    )

    glowy.transition_color_over_iterable(my_iterable, lambda: machine.process_event(time_out))

showing_long_break_early_notif.on_entry = long_early_notification_pulse


def long_late_notification_pulse():
    glowy.set_main_color(color_long)
    glowy.run_on_click = lambda: machine.process_event(break_started)

    my_iterable = gb.steady_pulse(steady_pulse_period / 2, color_long, color_late)
    glowy.transition_color_over_iterable(my_iterable, None)

showing_long_break_late_notif.on_entry = long_late_notification_pulse


def show_long_break_screen_countdown():
    next_long_break_clock_time = time.time()
    longy.set_layout_to_countdown()
    longy.showFullScreen()

long_break_in_progress.on_entry = show_long_break_screen_countdown


def show_long_break_screen_finished():
    longy.set_layout_to_finished()
    longy.showFullScreen()

long_break_finished.on_entry = show_long_break_screen_finished


################  Main
if __name__ == '__main__':

    ################  Logging
    logger = logging.getLogger()
    logging.basicConfig(
            level=logging.DEBUG,
            #format='%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s',
            )
    # For logging to cutelog
    socket_handler = SocketHandler('127.0.0.1', 19996)
    logger.addHandler(socket_handler)
    logger.info("Logging initialized")

    ################  Show colors
    logger.info("Here's a list of colors:  %s", QColor.colorNames())

    ################  Set up concurrent activities
    #threading.Thread(target=scheduler_thread, daemon=True).start()
    global_timer = QTimer()

    global next_long_break_clock_time
    next_long_break_clock_time = time.time() + long_break_spacing_time

    ################  Set up QT
    app = QApplication(sys.argv)

    glowy = gb.GlowBox()

    shorty = bs.ShortBreakScreen(length_of_short_break, lambda: machine.process_event(break_ended))
    longy = bs.LongBreakScreen(length_of_long_break, lambda: machine.process_event(time_out), lambda: machine.process_event(break_ended), lambda: machine.process_event(break_ended))

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

