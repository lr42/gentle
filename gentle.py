import math
import time
import logging
from logging.handlers import SocketHandler
import sys
import tomlkit

# pylint: disable=import-error
from PySide6.QtCore import QTimer, QUrl, QThread

# pylint: disable=import-error
from PySide6.QtGui import QAction, QIcon

# pylint: disable=import-error
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QSystemTrayIcon,
)

# pylint: disable=import-error
from PySide6.QtMultimedia import QSoundEffect

import stama.stama as sm
import glowbox as gb
import breakscreen as bs
import afk_worker as aw


# ##############  Events for the state machine
# fmt: off
time_out                = sm.Event("Time out")
break_started           = sm.Event("Break started")
break_ended             = sm.Event("Break ended")
afk_short_period_ended  = sm.Event("Short AFK period ended")
afk_long_period_ended   = sm.Event("Long AFK period ended")
returned_to_computer    = sm.Event("User returned to computer")
# fmt: on


# ##############  Set up conditional junction
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


# ##############  Short break state actions
def set_timer_for_short_break():
    # TODO This function (and probably others) is too long.  It needs to be refactored.
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

    next_short_break_per_clock = time.strftime(
        "%H:%M:%S", time.localtime(next_short_break_unix_time)
    )
    next_long_break_per_clock = time.strftime(
        "%H:%M:%S", time.localtime(next_long_break_unix_time)
    )

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


def clear_timeout_timer():
    global_timer.stop()


def show_short_break_early_notification():
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


def show_short_break_screen():
    shorty.showFullScreen()


def hide_short_break_screen():
    shorty.hide()


# ##############  Long break state actions
def set_timer_for_long_break():
    global next_long_break_unix_time
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

    next_long_break_per_clock = time.strftime(
        "%H:%M:%S", time.localtime(next_long_break_unix_time)
    )
    tooltip_next_break = "Next break (long): " + next_long_break_per_clock
    logger.info(tooltip_next_break)
    tray_icon.setToolTip(TOOLTIP_TITLE + "\n" + tooltip_next_break)

    global_timer.singleShot(
        secs_to_notification * 1000, lambda: machine.process_event(time_out)
    )


def show_long_break_early_notification():
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


def show_long_break_screen_countdown():
    global next_long_break_unix_time
    next_long_break_unix_time = time.time()
    longy.set_layout_to_countdown()
    longy.showFullScreen()


def show_long_break_screen_finished():
    longy.set_layout_to_finished()
    longy.showFullScreen()
    long_break_chime.play()


def reset_next_long_break_time():
    global next_long_break_unix_time
    next_long_break_unix_time = (
        time.time() + config["regular_break"]["spacing"]
    )
    logger.debug(
        "Resetting next long break to:  %s",
        time.strftime("%H:%M:%S", time.localtime(next_long_break_unix_time)),
    )


# ##############  Set up short break state sub-classes
class WaitingForShortBreak(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Waiting for a short break"

    def on_entry(self):
        set_timer_for_short_break()

    def on_exit(self):
        clear_timeout_timer()


class ShowingShortBreakEarlyNotif(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Showing the short break early notification"

    def on_entry(self):
        show_short_break_early_notification()

    def on_exit(self):
        # TODO Only hide the short break early notification if the late notification is not the next state....
        #  This currently shows a blink when transistioning to the late
        #  notification.  It's not a deal-breaker, but it's a distraction and a
        #  little detail that makes a difference.
        glowy.hide()


class ShowingShortBreakLateNotif(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Showing the short break late notification"

    def on_entry(self):
        show_short_break_late_notification()

    def on_exit(self):
        glowy.hide()


class ShortBreakInProgress(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Short break in progress"

    def on_entry(self):
        show_short_break_screen()

    def on_exit(self):
        hide_short_break_screen()


class WaitingAfterShortAfk(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Waiting after a short AFK timeout"

    def on_entry(self):
        # There's currently nothing we need to do in entering this state.
        pass

    def on_exit(self):
        # There's currently nothing we need to do in exiting this state.
        pass


# ##############  Set up long break state sub-classes
class WaitingForLongBreak(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Waiting for a long break"

    def on_entry(self):
        set_timer_for_long_break()

    def on_exit(self):
        clear_timeout_timer()


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
        glowy.hide()


class ShowingLongBreakLateNotif(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Showing the long break late notification"

    def on_entry(self):
        show_long_break_late_notification()

    def on_exit(self):
        glowy.hide()


class LongBreakInProgress(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "long break in progress"

    def on_entry(self):
        show_long_break_screen_countdown()

    def on_exit(self):
        reset_next_long_break_time()


class LongBreakFinished(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "long break finished"

    def on_entry(self):
        show_long_break_screen_finished()

    def on_exit(self):
        reset_next_long_break_time()


class WaitingAfterLongAfk(sm.State):
    def __init__(self):
        super().__init__()
        self.name = "Waiting after AFK for long duration"

    def on_exit(self):
        reset_next_long_break_time()


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

test_for_next_break             = sm.ConditionalJunction(
                                      waiting_for_long_break,
                                      "Testing for next break",
                                  )
# fmt: on


# ##############  Assigning functions to actions
# fmt: off


test_for_next_break.add_condition(
    has_short_break_before_long_break, waiting_for_short_break
)
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
    time_out:                   None,
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
    time_out:                   None,
    returned_to_computer:       test_for_next_break,
}
# fmt:on


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
        # TODO Maybe use separate colors for short and long early and late notifications?...
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
    logger.debug(
        "Setting next long break to:  %s",
        time.strftime("%H:%M:%S", time.localtime(next_long_break_unix_time)),
    )

    # ##############  Set up Qt
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

    # ##############  Add chime
    # TODO Make the chime settable in the configuration.
    # TODO Stop the chime when the user clicks "Let me get back to work".
    long_break_chime_file = "singing_bowl.wav"
    long_break_chime_volume = 0.5
    long_break_chime = QSoundEffect()
    long_break_chime.setSource(QUrl.fromLocalFile(long_break_chime_file))
    long_break_chime.setVolume(long_break_chime_volume)

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

    # ##############  Set up AFK listener
    # TODO The afk periods need to be longer than the "limbo" to "back at computer" timeout....
    #  Otherwise we end up in a situation where we can be in a "Waiting after
    #  AFK for long duration" state when we receive a "Short AFK period ended"
    #  event, which the first is not set up to handle.
    # TODO Make AFK times settable in the config.
    scheduled_events = {
        2 * 60: lambda: machine.process_event(afk_short_period_ended),
        10 * 60: lambda: machine.process_event(afk_long_period_ended),
    }

    afk_thread = QThread()
    afk_worker = aw.AFKWorker(
        # input_timeout = 1,
        # limbo_timeout_to_back = 1,
        scheduled_timeouts=list(scheduled_events.keys()),
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
        Stop timers and threads, before exiting the application.  (Otherwise we
        get errors complaining that we didn't.)
        """
        afk_worker.stopTimerSignal.emit()
        afk_thread.quit()
        afk_thread.wait()

    app.aboutToQuit.connect(cleanup)

    # ##############  Exit on QT app close
    sys.exit(app.exec())
