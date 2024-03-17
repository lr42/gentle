import math
import time
import logging
from logging.handlers import SocketHandler
import sys
import datetime
import tomlkit

# pylint: disable=import-error
from PySide6.QtCore import (
    QTimer,
)

# pylint: disable=import-error
from PySide6.QtGui import QAction, QIcon

# pylint: disable=import-error
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QSystemTrayIcon,
)

import stama.stama as sm
import glowbox as gb
import breakscreen as bs


# ##############  States


# fmt: off
waiting_for_short_break         = sm.State("Waiting for a short break")
showing_short_break_early_notif = sm.State("Showing the short break early notification")
showing_short_break_late_notif  = sm.State("Showing the short break late notification")
short_break_in_progress         = sm.State("Short break in progress")
waiting_after_short_afk         = sm.State("Waiting after AFK for short duration")

waiting_for_long_break          = sm.State("Waiting for a long break")
showing_long_break_early_notif  = sm.State("Showing the long break early notification")
showing_long_break_late_notif   = sm.State("Showing the long break late notification")
long_break_in_progress          = sm.State("long break in progress")
long_break_finished             = sm.State("long break finished")
waiting_after_long_afk          = sm.State("Waiting after AFK for long duration")

test_for_next_break             = sm.ConditionalJunction(
                                      waiting_for_long_break,
                                      "Testing for next break",
                                  )
# fmt: on


# ##############  Set up conditional junction


def has_short_break_before_long_break():
    global next_long_break_unix_time
    if time.time() > next_long_break_unix_time:
        logger.debug(
            "Resetting next long break to:  %s",
            datetime.datetime.fromtimestamp(
                next_long_break_unix_time
            ).strftime("%H:%M:%S"),
        )
        next_long_break_unix_time = (
            time.time() + config["regular_break"]["spacing"]
        )
    secs_to_long_break = next_long_break_unix_time - time.time()
    if config["short_break"]["max_spacing"] < secs_to_long_break:
        logger.debug(
            "has_short_break_before_long_break is True: %s < %s",
            config["short_break"]["max_spacing"],
            secs_to_long_break,
        )
        return True
    logger.debug(
        "has_short_break_before_long_break is False: %s >= %s",
        config["short_break"]["max_spacing"],
        secs_to_long_break,
    )
    return False


test_for_next_break.add_condition(
    has_short_break_before_long_break, waiting_for_short_break
)


# ##############  Events for the state machine


# fmt: off
time_out                = sm.Event("Time out")
break_started           = sm.Event("Break started")
break_ended             = sm.Event("Break ended")
afk_short_period_ended  = sm.Event("Short AFK period ended")
afk_long_period_ended   = sm.Event("Long AFK period ended")
returned_to_computer    = sm.Event("User returned to computer")
# fmt: on


# ##############  Short break transitions


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
    afk_long_period_ended:      None,  # TODO
    returned_to_computer:       None,  # TODO
}

waiting_after_short_afk.transitions = {
    afk_long_period_ended:      waiting_after_long_afk,
    returned_to_computer:       test_for_next_break,
}


# ##############  Long break transitions


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
    returned_to_computer:       None,  # TODO
}

long_break_finished.transitions = {
    break_ended:                test_for_next_break,
    afk_short_period_ended:     None,
    afk_long_period_ended:      None,
    returned_to_computer:       None,  # TODO
}

waiting_after_long_afk.transitions = {
    returned_to_computer:       test_for_next_break,
}
# fmt:on


# ##############  Short break state actions


def set_timer_for_short_break():
    # TODO This function (and probably others) is too long.  It needs to be
    #  refactored.
    secs_to_long_break = next_long_break_unix_time - time.time()
    logger.debug("secs_to_long_break:  %s", secs_to_long_break)

    num_segments_to_long_break = math.ceil(
        (secs_to_long_break + config["short_break"]["length"])
        / (
            config["short_break"]["length"]
            + config["short_break"]["max_spacing"]
        )
    )
    logger.debug("num_segments_to_long_break:  %s", num_segments_to_long_break)

    num_short_breaks_to_long_break = num_segments_to_long_break - 1
    logger.debug(
        "num_short_breaks_to_long_break:  %s", num_short_breaks_to_long_break
    )

    total_short_break_secs_to_long_break = (
        num_short_breaks_to_long_break * config["short_break"]["length"]
    )
    logger.debug(
        "total_short_break_secs_to_long_break:  %s",
        total_short_break_secs_to_long_break,
    )

    working_secs_to_long_break = (
        secs_to_long_break - total_short_break_secs_to_long_break
    )
    logger.debug("working_secs_to_long_break:  %s", working_secs_to_long_break)

    secs_to_short_break = (
        working_secs_to_long_break / num_segments_to_long_break
    )
    logger.debug("secs_to_short_break:  %s", secs_to_short_break)

    next_short_break_unix_time = time.time() + secs_to_short_break

    secs_to_notification = (
        secs_to_short_break - config["short_break"]["early_notification"]
    )
    logger.debug("secs_to_notification:  %s", secs_to_notification)

    # I had some situations where all the stuff above would sometimes return a
    #  negative time.  (This mostly/always happened when testing with very short
    #  timings.)  It turns out that QT -- not having a time machine built in --
    #  did not like that.  Setting the secs_to_notification to a minimum of 0
    #  was the easiest way to fix it.
    secs_to_notification = max(secs_to_notification, 0)

    # ##############  Convey information
    logger.debug(
        "%dm%0.1fs to next short break",
        int(secs_to_short_break // 60),
        secs_to_short_break % 60,
    )
    logger.debug(
        "%dm%0.1fs to notification",
        int(secs_to_notification // 60),
        secs_to_notification % 60,
    )

    next_short_break_per_clock = datetime.datetime.fromtimestamp(
        next_short_break_unix_time
    ).strftime("%H:%M:%S")
    next_long_break_per_clock = datetime.datetime.fromtimestamp(
        next_long_break_unix_time
    ).strftime("%H:%M:%S")

    tooltip_next_break = "Next break (short): " + next_short_break_per_clock
    tooltip_next_long = "Next long break: " + next_long_break_per_clock

    logger.info(tooltip_next_break)
    logger.info(tooltip_next_long)

    tray_icon.setToolTip(
        TOOLTIP_TITLE + "\n" + tooltip_next_break + "\n" + tooltip_next_long
    )

    # ##############  Start timer
    global_timer.singleShot(
        secs_to_notification * 1000, lambda: machine.process_event(time_out)
    )


def clear_time_out_timer():
    global_timer.stop()


def short_early_notification_pulse():
    glowy.set_main_color(config["colors"]["short"])
    glowy.run_on_click = lambda: machine.process_event(break_started)

    # TODO Should this include the color to show it as?
    glowy.show()

    # TODO Needs to come from configuration
    ending_fade_interval = config["general"]["steady_pulse_period"] / 2 / 1_000
    logger.debug("ending_fade_interval: %s", ending_fade_interval)
    starting_fade_multiplier = 5

    my_iterable = gb.intervals_decreasing_over_total_time(
        starting_fade_multiplier,
        ending_fade_interval,
        # This needs to be part of the GlowBox object.
        config["short_break"]["early_notification"],
        # TODO These need to be in the main program
        config["colors"]["short"],
        config["colors"]["early"],
    )

    glowy.transition_color_over_iterable(
        my_iterable, lambda: machine.process_event(time_out)
    )


def short_late_notification_pulse():
    glowy.set_main_color(config["colors"]["short"])
    glowy.run_on_click = lambda: machine.process_event(break_started)

    my_iterable = gb.steady_pulse(
        config["general"]["steady_pulse_period"] / 2,
        config["colors"]["short"],
        config["colors"]["late"],
    )
    glowy.transition_color_over_iterable(my_iterable, None)


def show_short_break_screen():
    shorty.showFullScreen()


def hide_short_break_screen():
    shorty.hide()


# ##############  Long break state actions


def set_timer_for_long_break():
    secs_to_long_break = next_long_break_unix_time - time.time()
    secs_to_notification = (
        secs_to_long_break - config["regular_break"]["early_notification"]
    )

    secs_to_notification = max(secs_to_notification, 0)

    logger.debug(
        "%dm%0.1fs to next long break",
        int(secs_to_long_break // 60),
        secs_to_long_break % 60,
    )
    logger.debug(
        "%dm%0.1fs to notification",
        int(secs_to_notification // 60),
        secs_to_notification % 60,
    )

    next_long_break_per_clock = datetime.datetime.fromtimestamp(
        next_long_break_unix_time
    ).strftime("%H:%M:%S")
    tooltip_next_break = "Next break (long): " + next_long_break_per_clock
    logger.info(tooltip_next_break)
    tray_icon.setToolTip(TOOLTIP_TITLE + "\n" + tooltip_next_break)

    global_timer.singleShot(
        secs_to_notification * 1000, lambda: machine.process_event(time_out)
    )


def long_early_notification_pulse():
    # TODO Should this be a setter?
    glowy.set_main_color(config["colors"]["regular"])
    glowy.run_on_click = lambda: machine.process_event(break_started)

    glowy.show()

    # TODO Needs to come from configuration
    ending_fade_interval = config["general"]["steady_pulse_period"] / 2 / 1_000
    logger.debug("ending_fade_interval: %s", ending_fade_interval)
    starting_fade_multiplier = 5

    my_iterable = gb.intervals_decreasing_over_total_time(
        starting_fade_multiplier,
        ending_fade_interval,
        # This needs to be part of the GlowBox object.
        config["regular_break"]["early_notification"],
        # TODO These need to be in the main program
        config["colors"]["regular"],
        config["colors"]["early"],
    )

    glowy.transition_color_over_iterable(
        my_iterable, lambda: machine.process_event(time_out)
    )


def long_late_notification_pulse():
    glowy.set_main_color(config["colors"]["regular"])
    glowy.run_on_click = lambda: machine.process_event(break_started)

    my_iterable = gb.steady_pulse(
        config["general"]["steady_pulse_period"] / 2,
        config["colors"]["regular"],
        config["colors"]["late"],
    )
    glowy.transition_color_over_iterable(my_iterable, None)


def show_long_break_screen_countdown():
    global next_long_break_unix_time
    next_long_break_unix_time = time.time()
    longy.set_layout_to_countdown()
    longy.showFullScreen()


def show_long_break_screen_finished():
    longy.set_layout_to_finished()
    longy.showFullScreen()


# ##############  Assigning functions to actions


# fmt: off
waiting_for_short_break.on_entry            = set_timer_for_short_break
waiting_for_short_break.on_exit             = clear_time_out_timer

showing_short_break_early_notif.on_entry    = short_early_notification_pulse

showing_short_break_late_notif.on_entry     = short_late_notification_pulse

short_break_in_progress.on_entry            = show_short_break_screen
short_break_in_progress.on_exit             = hide_short_break_screen


waiting_for_long_break.on_entry             = set_timer_for_long_break
waiting_for_long_break.on_exit              = clear_time_out_timer

showing_long_break_early_notif.on_entry     = long_early_notification_pulse

showing_long_break_late_notif.on_entry      = long_late_notification_pulse

long_break_in_progress.on_entry             = show_long_break_screen_countdown

long_break_finished.on_entry                = show_long_break_screen_finished
# fmt: on


# ##############  Functions used in __main__


def deep_update(a, b):
    if isinstance(b, dict):
        for key in b:
            if key in a and isinstance(a[key], dict):
                a[key] = deep_update(a[key], b[key])
            else:
                a[key] = b[key]
    else:
        a = b
    return a


# ##############  Main


if __name__ == "__main__":
    # ##############  Logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # For logging to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # For logging to cutelog
    socket_handler = SocketHandler("127.0.0.1", 19996)
    socket_handler.setLevel(logging.DEBUG)
    logger.addHandler(socket_handler)

    logger.debug("Logging initialized")

    # ##############  Default configuration
    config = {
        "general": {
            "steady_pulse_period": 1_000,
            "allow_skipping_short_breaks": True,
            "icon": "flower.png",
        },
        "regular_break": {
            "spacing": 3000,
            "length": 600,
            "early_notification": 120,
        },
        "short_break": {
            "max_spacing": 1200,
            "length": 20,
            "early_notification": 30,
        },
        # TODO Maybe use separate colors for short and long early and late notifications?
        #  Or at least leave that as an option?
        "colors": {
            "regular": "orchid",
            "short": "deepskyblue",
            "early": "white",
            "late": "yellow",
        },
    }

    # ##############  Load configuration from file
    CONFIGURATION_FILE = "./config.toml"
    try:
        with open(CONFIGURATION_FILE, "r", encoding="utf-8") as file:
            logger.debug("Default config:  %s", config)

            toml_config = tomlkit.load(file)
            logger.debug("Config from file:  %s", toml_config)

            config = deep_update(config, toml_config)
            logger.debug("Final config:  %s", config)

    except FileNotFoundError:
        logger.info(
            "Configuration file (%s) not found, using defaults.",
            CONFIGURATION_FILE,
        )

    # ##############  Set up concurrent activities
    global_timer = QTimer()

    next_long_break_unix_time = (
        time.time() + config["regular_break"]["spacing"]
    )

    # ##############  Set up QT
    app = QApplication(sys.argv)

    glowy = gb.GlowBox()

    if config["general"]["allow_skipping_short_breaks"]:
        shorty = bs.ShortBreakScreen(
            config["short_break"]["length"],
            lambda: machine.process_event(break_ended),
            lambda: machine.process_event(break_ended),
        )
    else:
        shorty = bs.ShortBreakScreen(
            config["short_break"]["length"],
            lambda: machine.process_event(break_ended),
        )

    longy = bs.LongBreakScreen(
        config["regular_break"]["length"],
        lambda: machine.process_event(time_out),
        lambda: machine.process_event(break_ended),
        lambda: machine.process_event(break_ended),
    )

    # ##############  Add tray icon
    tray_icon = QSystemTrayIcon(QIcon(config["general"]["icon"]))

    tray_menu = QMenu()
    action = QAction("Exit", tray_icon)
    action.triggered.connect(app.quit)
    tray_menu.addAction(action)
    tray_icon.setContextMenu(tray_menu)

    TOOLTIP_TITLE = "Gentle Break Reminder"
    tray_icon.setToolTip(TOOLTIP_TITLE)

    tray_icon.show()

    # ##############  Start state machine
    machine = sm.StateMachine(waiting_for_short_break)

    # ##############  Exit on QT app close
    sys.exit(app.exec())
