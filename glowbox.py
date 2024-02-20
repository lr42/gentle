"""Creates a pulsing box on the screen that can execute actions when it's clicked"""

import datetime  # TODO Temporary
import json
import shutil
import logging
# pylint: disable=import-error
from PySide6.QtCore import (
    Qt,
    QPropertyAnimation,
    Property,
    QEasingCurve,
)
# pylint: disable=import-error
from PySide6.QtGui import QAction, QColor, QPalette
# pylint: disable=import-error
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QSizeGrip,
    QMenu,
)


logger = logging.getLogger(__name__)


class GlowBox(QWidget):
    """Creates a pulsing box on the screen that can execute actions when it's clicked"""
    color = Property(
        QColor,
        lambda self: self.palette().color(QPalette.Window),
        lambda self, color: self.setPalette(QPalette(color)),
    )

    def __init__(self):
        super().__init__()

        self.color_main = "deepskyblue"
        self.color_early = "white"
        self.color_late = "yellow"

        self.steady_pulse_period = 1000

        self.setWindowTitle("Gentle break reminder")  # This might be obsolete some day.

        ################################################################

        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.ToolTip  # This makes the window stay off the task bar
            | Qt.X11BypassWindowManagerHint
        )

        self.setMinimumSize(15, 15)

        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # TODO Magic
        self.setWindowOpacity(0.7)

        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(self.color_main))
        self.setPalette(palette)

        grip_size = 5
        self.grip = QSizeGrip(self)
        self.grip.resize(grip_size, grip_size)
        self.grip.setVisible(True)

        self.is_cycling_from_main_color = True

        self.use_saved_window_geometry()

        # TODO What the heck is this?
        print("And we're back")

        rect = self.geometry()
        logger.debug("Geometry: %s", rect)
        self.starting_geometry = {
            "location_x": rect.x(),
            "location_y": rect.y(),
            "width": rect.width(),
            "height": rect.height(),
        }

        self.offset = None
        self.is_moving = None
        self.previous_position = None

        self.color_animation = QPropertyAnimation(self, b"color")

    ################  QT QWidget overrides

    # pylint: disable=invalid-name
    def mousePressEvent(self, event):
        self.offset = event.position().toPoint()
        self.is_moving = True
        self.previous_position = event.globalPosition().toPoint()

    # pylint: disable=invalid-name
    def mouseMoveEvent(self, event):
        if self.is_moving:
            self.move(event.globalPosition().toPoint() - self.offset)

    # pylint: disable=invalid-name
    def mouseReleaseEvent(self, event):
        if event.globalPosition().toPoint() == self.previous_position:
            # TODO We don't really need this.  We need proper logging.
            print(datetime.datetime.now())
            print("BAZINGA!!!")

            self.close_and_save_geometry()
        self.is_moving = False

    # pylint: disable=invalid-name
    def contextMenuEvent(self, ev):
        close_action = QAction("Close program", self)
        close_action.triggered.connect(self.close_and_save_geometry)

        context = QMenu(self)
        context.addAction(QAction("test 1", self))
        context.addAction(QAction("test 2", self))
        context.addAction(close_action)
        context.exec(ev.globalPos())

    ################  Changing the color

    def transition_to_color(self, transition, on_fade_done=None):
        logger.debug("Transitioning color to %s", transition)
        self.color_animation.setEndValue(QColor(transition['new_color']))
        self.color_animation.setDuration(transition['duration'])
        # TODO Magic
        default_transitition = QEasingCurve.InOutSine
        if 'easing curve' in transition:
            self.color_animation.setEasingCurve(transition['easing curve'])
        else:
            self.color_animation.setEasingCurve(default_transitition)
        self.color_animation.start()
        if on_fade_done:
            try:
                self.color_animation.finished.disconnect()
            except (RuntimeError) as e:
                logger.info("%s -- There was probably nothing previously connected to the animation finishing.", e)
            self.color_animation.finished.connect(on_fade_done)

    def transition_color_over_iterable(self, transitions, run_on_completion):
        def handle_next_transition():
            try:
                self.transition_to_color(next(transitions), handle_next_transition)
            except (StopIteration):
                if run_on_completion:
                    run_on_completion()

        handle_next_transition()

    ################  The old way
    # I should be able to remove this soon.

    def change_pulse_over_time(self, list_of_intervals, current_interval=0):
        if current_interval % 2 == 0:
            new_color = self.color_early
        else:
            new_color = self.color_main

        # logger.info("Fading to {} over {} ms".format(new_color, list_of_intervals[current_interval]))
        if current_interval >= len(list_of_intervals) - 1:
            self.fade_color(
                new_color, list_of_intervals[current_interval], self.steady_pulse
            )
        else:
            self.fade_color(
                new_color,
                list_of_intervals[current_interval],
                lambda: self.change_pulse_over_time(
                    list_of_intervals, current_interval + 1
                ),
            )

    def steady_pulse(self):
        if self.is_cycling_from_main_color:
            new_color = self.color_late
        else:
            new_color = self.color_main
        self.fade_color(new_color, self.steady_pulse_period / 2, self.steady_pulse)
        self.is_cycling_from_main_color = not self.is_cycling_from_main_color

    def fade_color(self, new_color, duration, on_fade_done=False):
        self.color_animation.setEndValue(QColor(new_color))
        self.color_animation.setDuration(duration)
        self.color_animation.start()
        # TODO Magic
        self.color_animation.setEasingCurve(QEasingCurve.InOutSine)
        if on_fade_done:
            self.color_animation.finished.connect(on_fade_done)

    ################  Window geometry

    def save_window_geometry(self, filename="geometry.json"):
        rect = self.geometry()
        # logger.info(rect)

        geometry = {
            "location_x": rect.x(),
            "location_y": rect.y(),
            "width": rect.width(),
            "height": rect.height(),
        }

        if (
            geometry["location_x"] != self.starting_geometry["location_x"]
            or geometry["location_y"] != self.starting_geometry["location_y"]
            or geometry["width"] != self.starting_geometry["width"]
            or geometry["height"] != self.starting_geometry["height"]
        ):
            # logger.info("Saving window geometry")
            # logger.info(geometry)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(geometry, f, indent=2)
        else:
            # logger.info("Window not moved")
            pass

    def close_and_save_geometry(self):
        # logger.info("Closing time")
        self.save_window_geometry()
        self.hide()

    def use_saved_window_geometry(self, filename="geometry.json"):
        # logger.info("Setting geometry", filename)
        try:
            with open(filename, "r", encoding="utf-8") as f:
                geometry = json.load(f)
            # logger.info(geometry)
            self.setGeometry(
                geometry["location_x"],
                geometry["location_y"],
                geometry["width"],
                geometry["height"],
            )
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.info("Could not parse file: %s  (%s)", filename, e)
            try:
                shutil.copy2(filename, filename+".backup")
            except (FileNotFoundError) as e2:
                logger.info("Could not make a backup  (%s)", e2)
            print("Moving on")
            zsize = QApplication.screens()[0].size()
            # TODO Magic numbers
            logger.info(zsize)
            glowbox_width = 100
            glowbox_height = 100
            x = (zsize.width() - glowbox_width) / 2
            y = (zsize.height() - glowbox_height) / 2
            logger.info(x, y)
            self.setGeometry(x, y, glowbox_width, glowbox_height)


def nearest_even(n):
    if n % 2 == 1:
        return n - 1
    return int(round(n / 2) * 2)


def intervals_decreasing_over_total_time(
    rough_starting_interval, ending_interval, total_time, main_color, secondary_color, to_nearest_even_number=True
):
    logger.debug("Starting intervals_decreasing_over_total_time(%s, %s, %s)", rough_starting_interval, ending_interval, total_time)

    unrounded_number_of_intervals = 2 * total_time / (rough_starting_interval + ending_interval)
    logger.debug("Approximate number of intervals: %s", unrounded_number_of_intervals)

    if to_nearest_even_number:
        final_number_of_intervals = int(nearest_even(unrounded_number_of_intervals))
    logger.debug("Final number of intervals: %s", final_number_of_intervals)

    new_starting_interval = (2 * total_time / final_number_of_intervals) - ending_interval
    logger.debug("New starting interval: %s", new_starting_interval)

    total_time / ((new_starting_interval / 2) + ending_interval)

    (((new_starting_interval - ending_interval) / 2) + ending_interval) * final_number_of_intervals

    #intervals = []
    for i in range(final_number_of_intervals):
        slope = (ending_interval - new_starting_interval) / final_number_of_intervals
        # We add 0.5, because we want to get the timing of the interval
        #  from the slope of the equation at the middle of the interval.
        #  (Since the slope is linear, you can the whole time taken by
        #  the interval is the time at the midpoint of the interval...
        # I dunno how exactly to say what I was saying there.  Imma come
        #  back to it.  TODO.
        next = new_starting_interval + ((i + 0.5) * slope)
        next *= 1_000
        next = int(next)

        #logger.info("i: %s", i)
        if i % 2 == 0:
            color = secondary_color
        else:
            color = main_color

        yield {'new_color': color, 'duration': next}
        # logger.info(i, "\t", next, "\t", sum(intervals)/1_000)

    return
