# coding: utf-8

import math
import time
import logging
from logging.handlers import SocketHandler
import sys
import tomlkit

# pylint: disable=import-error
from PySide6.QtCore import QTimer, QUrl, QThread

# pylint: disable=import-error
from PySide6.QtGui import QAction, QIcon, QPixmap

# pylint: disable=import-error
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QSystemTrayIcon,
    QSplashScreen,
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

# pylint: disable=import-error
from PySide6.QtMultimedia import QSoundEffect

import stama.stama as sm
import glowbox as gb
import breakscreen as bs
import afk_worker as aw


TIME_FORMAT = "%-I:%M:%S %p"
TOOLTIP_TITLE = "Gentle Break Reminder"
TOOLTIP_TIMER_INTERVAL = 3000  # in ms


# ##############  Logging
SUCCESS = 25
logging.addLevelName(25, "SUCCESS")

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# For logging to the console
console_formatter = logging.Formatter(
    fmt="%(asctime)s - %(message)s", datefmt=TIME_FORMAT
)
console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)
console_handler.setLevel(SUCCESS)
logger.addHandler(console_handler)

# For logging to cutelog
socket_handler = SocketHandler("127.0.0.1", 19996)
socket_handler.setLevel(0)
logger.addHandler(socket_handler)

logger.debug("Logging initialized")


# ##############  Events for the state machine
# fmt: off
short_break_due_timeout         = sm.Event("Short break due timeout")
short_break_early_notif_timeout = sm.Event("Short break early notification timeout")
long_break_due_timeout          = sm.Event("Long break due timeout")
long_break_early_notif_timeout  = sm.Event("Long break early notification timeout")
long_break_finished_timeout     = sm.Event("Long break finished")
break_started                   = sm.Event("Break started")
break_ended                     = sm.Event("Break ended")
afk_short_period_ended          = sm.Event("Short AFK period ended")
afk_long_period_ended           = sm.Event("Long AFK period ended")
returned_to_computer            = sm.Event("User returned to computer")
# fmt: on


# ##############  Short break state actions
def set_timer_for_short_break():
    # TODO This function (and probably others) is too long.  It needs to be refactored.
    global next_long_break_unix_time
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

    global next_short_break_unix_time
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

    next_short_break_per_clock = time.strftime(
        config["general"]["time_format"],
        time.localtime(next_short_break_unix_time),
    )
    next_long_break_per_clock = time.strftime(
        config["general"]["time_format"],
        time.localtime(next_long_break_unix_time),
    )

    logger.log(SUCCESS, "Next break (short): %s", next_short_break_per_clock)
    logger.log(SUCCESS, "Next long break: %s", next_long_break_per_clock)

    # ##############  Set system tray tool tip
    set_system_tray_tool_tip_text()
    global tooltip_update_timer
    tooltip_update_timer.start(TOOLTIP_TIMER_INTERVAL)

    # ##############  Start timer
    global short_break_timer
    short_break_timer.start(secs_to_notification * 1000)


def show_short_break_early_notification():
    global glowy
    glowy.set_main_color(config["colors"]["short"])
    glowy.run_on_click = lambda: machine.process_event(break_started)

    # TODO Should this include the color to show it as?
    glowy.show()

    ending_fade_interval = config["general"]["steady_pulse_period"] / 2 / 1_000
    logger.debug("ending_fade_interval: %s", ending_fade_interval)
    starting_fade_multiplier = 5

    my_iterable = gb.intervals_decreasing_over_total_time(
        starting_fade_multiplier,
        ending_fade_interval,
        config["short_break"]["early_notification"],
        config["colors"]["short"],
        config["colors"]["early"],
    )

    global machine
    glowy.transition_color_over_iterable(
        my_iterable,
        lambda: machine.process_event(short_break_early_notif_timeout),
    )


def show_short_break_late_notification():
    glowy.set_main_color(config["colors"]["short"])
    glowy.run_on_click = lambda: machine.process_event(break_started)

    glowy.show()

    my_iterable = gb.steady_pulse(
        config["general"]["steady_pulse_period"] / 2,
        config["colors"]["short"],
        config["colors"]["late"],
    )
    glowy.transition_color_over_iterable(my_iterable, None)


# ##############  Long break state actions
def set_timer_for_long_break():
    global next_long_break_unix_time
    secs_to_long_break = next_long_break_unix_time - time.time()
    secs_to_notification = (
        secs_to_long_break - config["long_break"]["early_notification"]
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

    next_long_break_per_clock = time.strftime(
        config["general"]["time_format"],
        time.localtime(next_long_break_unix_time),
    )

    logger.log(SUCCESS, "Next break (long): %s", next_long_break_per_clock)

    global tooltip_update_timer, next_short_break_unix_time
    next_short_break_unix_time = None
    set_system_tray_tool_tip_text()
    tooltip_update_timer.start(TOOLTIP_TIMER_INTERVAL)

    global long_break_timer
    long_break_timer.start(secs_to_notification * 1000)


def show_long_break_early_notification():
    # TODO Should this be a setter?
    glowy.set_main_color(config["colors"]["regular"])
    glowy.run_on_click = lambda: machine.process_event(break_started)

    glowy.show()

    ending_fade_interval = config["general"]["steady_pulse_period"] / 2 / 1_000
    logger.debug("ending_fade_interval: %s", ending_fade_interval)
    starting_fade_multiplier = 5

    my_iterable = gb.intervals_decreasing_over_total_time(
        starting_fade_multiplier,
        ending_fade_interval,
        config["long_break"]["early_notification"],
        config["colors"]["regular"],
        config["colors"]["early"],
    )

    glowy.transition_color_over_iterable(
        my_iterable,
        lambda: machine.process_event(long_break_early_notif_timeout),
    )


def show_long_break_late_notification():
    glowy.set_main_color(config["colors"]["regular"])
    glowy.run_on_click = lambda: machine.process_event(break_started)

    glowy.show()

    my_iterable = gb.steady_pulse(
        config["general"]["steady_pulse_period"] / 2,
        config["colors"]["regular"],
        config["colors"]["late"],
    )
    glowy.transition_color_over_iterable(my_iterable, None)


def reset_next_long_break_time():
    global next_long_break_unix_time
    global config
    next_long_break_unix_time = time.time() + config["long_break"]["spacing"]
    logger.debug(
        "Resetting next long break to:  %s",
        time.strftime(
            config["general"]["time_format"],
            time.localtime(next_long_break_unix_time),
        ),
    )


# ##############  Generic state actions
def set_static_tool_tip_text(text):
    global tray_icon, tooltip_update_timer
    tooltip_update_timer.stop()
    tray_icon.setToolTip("<b>" + TOOLTIP_TITLE + "</b><br>" + text)


# ##############  Set up short break state sub-classes
class WaitingForShortBreak(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Waiting for a short break"

    def on_entry(self):
        set_timer_for_short_break()

    def on_exit(self):
        short_break_timer.stop()


class ShowingShortBreakEarlyNotif(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Showing the short break early notification"

    def on_entry(self):
        show_short_break_early_notification()

    # TODO Only hide the short break early notification if the late notification is not the next state....
    #  This currently shows a blink when transistioning to the late
    #  notification.  It's not a deal-breaker, but it's a distraction and a
    #  little detail that makes a difference.
    def on_exit(self):
        glowy.close_and_save_geometry()


class ShowingShortBreakLateNotif(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Showing the short break late notification"

    def on_entry(self):
        show_short_break_late_notification()

    def on_exit(self):
        glowy.close_and_save_geometry()


class ShortBreakInProgress(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Short break in progress"

    def on_entry(self):
        global shorty
        shorty.showFullScreen()
        set_static_tool_tip_text("Short break in progress")
        logger.log(SUCCESS, "Taking a short break.")

    def on_exit(self):
        shorty.hide()
        logger.log(SUCCESS, "Short break finished.")


class WaitingAfterShortAfk(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Waiting after a short AFK timeout"

    def on_entry(self):
        global tray_icon
        set_static_tool_tip_text("Away from keyboard (short)")
        logger.log(
            SUCCESS, "Away from the computer enough to reset the short break."
        )

    def on_exit(self):
        pass


# ##############  Set up long break state sub-classes
class WaitingForLongBreak(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Waiting for a long break"

    def on_entry(self):
        set_timer_for_long_break()

    def on_exit(self):
        long_break_timer.stop()


class ShowingLongBreakEarlyNotif(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Showing the long break early notification"

    def on_entry(self):
        show_long_break_early_notification()

    def on_exit(self):
        # TODO Only hide the short break early notification if the late notification is not the next state....
        #  This currently shows a blink when transistioning to the late
        #  notification.  It's not a deal-breaker, but it's a distraction and a
        #  little detail that makes a difference.
        glowy.close_and_save_geometry()


class ShowingLongBreakLateNotif(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Showing the long break late notification"

    def on_entry(self):
        show_long_break_late_notification()

    def on_exit(self):
        glowy.close_and_save_geometry()


class LongBreakInProgress(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Long break in progress"

    def on_entry(self):
        global longy
        longy.set_layout_to_countdown()
        longy.showFullScreen()
        set_static_tool_tip_text("Long break in progress")
        logger.log(SUCCESS, "Taking a long break.")

    def on_exit(self):
        reset_next_long_break_time()


class LongBreakFinished(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Long break finished"

    def on_entry(self):
        global long_break_chime
        longy.set_layout_to_finished()
        longy.showFullScreen()
        long_break_chime.play()
        set_static_tool_tip_text("Long break finished")

    def on_exit(self):
        reset_next_long_break_time()
        logger.log(SUCCESS, "Getting back to work!")


class WaitingAfterLongAfk(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Waiting after a long AFK timeout"

    def on_entry(self):
        set_static_tool_tip_text("Away from keyboard (long)")
        logger.log(
            SUCCESS, "Away from the computer enough to reset the long break."
        )

    def on_exit(self):
        reset_next_long_break_time()
        logger.log(SUCCESS, "Back at the computer.")


# ##############  Set up conditional junction boolean
def has_short_break_before_long_break():
    global next_long_break_unix_time
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


# ##############  Set up junctions
class TestForNextBreak(sm.ConditionalJunction):
    def __init__(self):
        super().__init__(
            default_state=waiting_for_long_break, name="Testing for next break"
        )
        self.add_condition(
            has_short_break_before_long_break, waiting_for_short_break
        )


# ##############  States
# fmt: off
waiting_for_short_break         = WaitingForShortBreak()
showing_short_break_early_notif = ShowingShortBreakEarlyNotif()
showing_short_break_late_notif  = ShowingShortBreakLateNotif()
short_break_in_progress         = ShortBreakInProgress()
waiting_after_short_afk         = WaitingAfterShortAfk()

waiting_for_long_break          = WaitingForLongBreak()
showing_long_break_early_notif  = ShowingLongBreakEarlyNotif()
showing_long_break_late_notif   = ShowingLongBreakLateNotif()
long_break_in_progress          = LongBreakInProgress()
long_break_finished             = LongBreakFinished()
waiting_after_long_afk          = WaitingAfterLongAfk()

test_for_next_break             = TestForNextBreak()


# ##############  Short break transitions
waiting_for_short_break.transitions = {
    short_break_due_timeout:            showing_short_break_early_notif,
    afk_short_period_ended:             waiting_after_short_afk,
    afk_long_period_ended:              waiting_after_long_afk,
    returned_to_computer:               None,
}

showing_short_break_early_notif.transitions = {
    short_break_early_notif_timeout:    showing_short_break_late_notif,
    break_started:                      short_break_in_progress,
    break_ended:                        test_for_next_break,  # Skipping the break
    afk_short_period_ended:             waiting_after_short_afk,
    afk_long_period_ended:              waiting_after_long_afk,
    returned_to_computer:               None,
}

showing_short_break_late_notif.transitions = {
    break_started:                      short_break_in_progress,
    break_ended:                        test_for_next_break,  # Skipping the break
    afk_short_period_ended:             waiting_after_short_afk,
    afk_long_period_ended:              waiting_after_long_afk,
    returned_to_computer:               None,
}

short_break_in_progress.transitions = {
    break_ended:                        test_for_next_break,
    afk_short_period_ended:             None,
    afk_long_period_ended:              None,  # TODO
    returned_to_computer:               None,  # TODO
}

waiting_after_short_afk.transitions = {
    short_break_due_timeout:            None,
    long_break_due_timeout:             None,
    afk_long_period_ended:              waiting_after_long_afk,
    returned_to_computer:               test_for_next_break,
}


# ##############  Long break transitions
waiting_for_long_break.transitions = {
    long_break_due_timeout:             showing_long_break_early_notif,
    afk_short_period_ended:             None,
    afk_long_period_ended:              waiting_after_long_afk,
    returned_to_computer:               None,
}

showing_long_break_early_notif.transitions = {
    long_break_early_notif_timeout:     showing_long_break_late_notif,
    break_started:                      long_break_in_progress,
    break_ended:                        test_for_next_break,  # Skipping the break
    afk_short_period_ended:             None,
    afk_long_period_ended:              waiting_after_long_afk,
    returned_to_computer:               None,
}

showing_long_break_late_notif.transitions = {
    break_started:                      long_break_in_progress,
    break_ended:                        test_for_next_break,  # Skipping the break
    afk_short_period_ended:             None,
    afk_long_period_ended:              waiting_after_long_afk,
    returned_to_computer:               None,
}

long_break_in_progress.transitions = {
    long_break_finished_timeout:        long_break_finished,
    break_ended:                        test_for_next_break,  # Skipping the break
    afk_short_period_ended:             None,
    afk_long_period_ended:              None,
    # TODO If the user starts uses the computer during a break, pause the break....
    #  However, this should be handled by the AFK status, not by the
    #  returned_to_computer State in the general state machine.
    returned_to_computer:               None,
}

long_break_finished.transitions = {
    break_ended:                        test_for_next_break,
    afk_short_period_ended:             None,
    afk_long_period_ended:              None,
    # TODO If the user starts uses the computer after a break is finished, consider the break as done....
    #  However, this should probably be handled by the AFK status, not by the
    #  returned_to_computer State in the general state machine.  (But I see no
    #  reason why doing both would break anything.  Of course it's the AFK
    #  state the triggers the returned_to_computer state.  Maybe I could use
    #  returned_to_computer as a stopgap until I set it up to use the AFK
    #  status?
    returned_to_computer:               None,
}

waiting_after_long_afk.transitions = {
    short_break_due_timeout:            None,
    long_break_due_timeout:             None,
    returned_to_computer:               test_for_next_break,
}
# fmt:on


# ##############  Functions repeating on a timed interval
def get_relative_due_time(seconds):
    # TODO Use doc tests in this function.
    closest_minute = (seconds + 30) // 60
    if closest_minute == 0:
        return "Due right now"
    elif closest_minute == -1:
        return "Past due by about 1 minute"
    elif closest_minute < -1:
        return "Past due by about {:.0f} minutes".format(-closest_minute)
    elif closest_minute == 1:
        return "In about 1 minute"
    elif closest_minute > 1:
        return "In about {:.0f} minutes".format(closest_minute)


def get_tooltip_break_message(
    next_break_unix_time, time_format, show_clock_times, show_relative_times
):
    secs_to_break = next_break_unix_time - time.time()

    if show_clock_times:
        next_break_per_clock = time.strftime(
            time_format,
            time.localtime(next_break_unix_time),
        )
        if show_relative_times:
            next_break_relative = get_relative_due_time(secs_to_break)
            return "<br>{}<br>({})".format(
                next_break_relative, next_break_per_clock
            )
        else:
            return "<br>{}".format(next_break_per_clock)
    else:
        if show_relative_times:
            next_break_relative = get_relative_due_time(secs_to_break)
            return "<br>{}".format(next_break_relative)
        else:
            return ""


def set_system_tray_tool_tip_text():
    global next_long_break_unix_time, next_short_break_unix_time

    next_long_break_message = get_tooltip_break_message(
        next_long_break_unix_time,
        config["general"]["time_format"],
        config["general"]["show_clock_times"],
        config["general"]["show_relative_times"],
    )

    tooltip_message = ""

    if not (
        config["general"]["show_clock_times"]
        or config["general"]["show_relative_times"]
    ):
        tooltip_message = ""
    elif next_short_break_unix_time is not None:
        next_short_break_message = get_tooltip_break_message(
            next_short_break_unix_time,
            config["general"]["time_format"],
            config["general"]["show_clock_times"],
            config["general"]["show_relative_times"],
        )

        tooltip_message += "<br><u>Next break (short):</u>"
        tooltip_message += next_short_break_message

        tooltip_message += "<br><u>Next long break:</u>"
        tooltip_message += next_long_break_message
    else:
        tooltip_message += "<br><u>Next break (long):</u>"
        tooltip_message += next_long_break_message

    global tray_icon
    tray_icon.show()
    tray_icon.setToolTip("<b>" + TOOLTIP_TITLE + "</b>" + tooltip_message)


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


def show_splash_screen(image, timeout=3000):
    pixmap = QPixmap(image)
    splash = QSplashScreen(pixmap)
    splash.show()
    QTimer.singleShot(timeout, lambda: splash.close())


class AboutWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("About")
        self.setHidden(True)

        layout = QVBoxLayout()

        label = QLabel(
            '<h1>Gentle Break Reminder</h1><p>An awesome little program for reminding you to take breaks.</p><p>See <a href="https://github.com/lr42/gentle">the website</a> for more information.</p>'
        )
        label.setOpenExternalLinks(True)
        layout.addWidget(label)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.hide)
        layout.addWidget(close_button)

        self.setLayout(layout)


# ##############  Main
def main():
    # ##############  Default configuration
    global config
    config = {
        "general": {
            "steady_pulse_period": 1_000,
            "allow_skipping_short_breaks": True,
            "icon": "flower.png",
            "time_format": TIME_FORMAT,
            "show_relative_times": True,
            "show_clock_times": False,
            "splash_screen_timeout": 5_000,
        },
        "long_break": {
            "spacing": 50 * 60,
            "length": 10 * 60,
            "early_notification": 2 * 60,
            "chime": "long_chime.wav",
        },
        "short_break": {
            "max_spacing": 20 * 60,
            "length": 20,
            "early_notification": 30,
        },
        # TODO Maybe use separate colors for short and long early and late notifications?...
        #  Or at least leave that as an option?
        "colors": {
            "regular": "orchid",
            "short": "deepskyblue",
            "early": "white",
            "late": "yellow",
        },
        "afk_options": {},
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

    # ##############  Adjust console logger with configured time format
    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(message)s",
        datefmt=config["general"]["time_format"],
    )
    console_handler.setFormatter(console_formatter)

    # ##############  Set up concurrent timers
    global short_break_timer
    short_break_timer = QTimer(
        singleShot=True,
        timeout=lambda: machine.process_event(short_break_due_timeout),
    )
    global long_break_timer
    long_break_timer = QTimer(
        singleShot=True,
        timeout=lambda: machine.process_event(long_break_due_timeout),
    )

    reset_next_long_break_time()

    # ##############  Set up Qt
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if config["general"]["splash_screen_timeout"] > 0:
        show_splash_screen(
            "splash_screen.png", config["general"]["splash_screen_timeout"]
        )

    global glowy
    glowy = gb.GlowBox()

    global shorty
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

    global longy
    longy = bs.LongBreakScreen(
        config["long_break"]["length"],
        lambda: machine.process_event(long_break_finished_timeout),
        lambda: machine.process_event(break_ended),
        lambda: machine.process_event(break_ended),
    )

    # ##############  Add chime
    # TODO Stop the chime when the user clicks "Let me get back to work".
    long_break_chime_file = config["long_break"]["chime"]
    long_break_chime_volume = 0.5
    global long_break_chime
    long_break_chime = QSoundEffect()
    long_break_chime.setSource(QUrl.fromLocalFile(long_break_chime_file))
    long_break_chime.setVolume(long_break_chime_volume)

    # ##############  Add tray icon
    global tray_icon
    tray_icon = QSystemTrayIcon(QIcon(config["general"]["icon"]))

    tray_menu = QMenu()

    about_window = AboutWindow()

    about_action = QAction("About", tray_icon)
    about_action.triggered.connect(about_window.show)
    tray_menu.addAction(about_action)

    exit_action = QAction("Exit", tray_icon)
    exit_action.triggered.connect(app.quit)
    tray_menu.addAction(exit_action)

    tray_icon.setContextMenu(tray_menu)

    tray_icon.setToolTip(TOOLTIP_TITLE)

    tray_icon.show()

    # ##############  Set up system tray icon tool tip timer
    global tooltip_update_timer, next_short_break_unix_time
    next_short_break_unix_time = None
    tooltip_update_timer = QTimer(timeout=set_system_tray_tool_tip_text)
    tooltip_update_timer.start(TOOLTIP_TIMER_INTERVAL)

    # ##############  Start state machine
    logger.log(SUCCESS, "Welcome to the Gentle Break Reminder!")

    global machine
    machine = sm.StateMachine(waiting_for_short_break)

    # ##############  Set up AFK listener
    # TODO The afk periods need to be longer than the "limbo" to "back at computer" timeout....
    #  Otherwise we end up in a situation where we can be in a "Waiting after
    #  AFK for long duration" state when we receive a "Short AFK period ended"
    #  event, which the first is not set up to handle.
    scheduled_events = {}
    if (
        config["away_from_keyboard"]["short_break_timeout"]
        >= config["away_from_keyboard"]["long_break_timeout"]
    ):
        logger.error(
            "The short break AFK timeout is set to be the same as or longer than the long break AFK timeout.  This makes no sense, and the AFK short break timeout will not be set."
        )
    elif config["away_from_keyboard"]["short_break_timeout"] > 0:
        scheduled_events[
            config["away_from_keyboard"]["short_break_timeout"]
        ] = lambda: machine.process_event(afk_short_period_ended)

    if config["away_from_keyboard"]["long_break_timeout"] > 0:
        scheduled_events[
            config["away_from_keyboard"]["long_break_timeout"]
        ] = lambda: machine.process_event(afk_long_period_ended)

    afk_thread = QThread()
    afk_worker = aw.AFKWorker(
        scheduled_timeouts=list(scheduled_events.keys()),
        **config["afk_options"],
    )

    afk_worker.scheduled_signal.connect(lambda t: scheduled_events[t]())

    afk_worker.at_computer_signal.connect(
        lambda t: machine.process_event(returned_to_computer)
    )

    afk_worker.moveToThread(afk_thread)
    afk_thread.started.connect(afk_worker.start_worker)
    afk_thread.start()

    # ##############  Clean up AFK thread on exit
    def cleanup():
        """
        Stop timers and threads before exiting the application.  (Otherwise we
        get errors complaining that we didn't.)
        """
        afk_worker.stopTimerSignal.emit()
        afk_thread.quit()
        afk_thread.wait()

    app.aboutToQuit.connect(cleanup)

    # ##############  Exit on QT app close
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
