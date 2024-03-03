"""Creates a pulsing box on the screen that can execute actions when it's clicked"""

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
from PySide6.QtGui import QColor, QPalette  # , QAction

# pylint: disable=import-error
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QSizeGrip,
    # QMenu,
)


logger = logging.getLogger(__name__)


class GlowBox(QWidget):
    """Creates a pulsing box on the screen that can execute actions when it's clicked"""

    color = Property(
        QColor,
        lambda self: self.palette().color(QPalette.Window),
        lambda self, color: self.setPalette(QPalette(color)),
    )

    def __init__(self, run_on_click=None):
        super().__init__()

        self.run_on_click = run_on_click

        self.setWindowTitle("Gentle break reminder")

        # # # # # # # #################################################

        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.ToolTip  # This makes the window stay off the task bar
            | Qt.X11BypassWindowManagerHint
        )

        self.setMinimumSize(15, 15)

        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # TODO Magic number
        self.setWindowOpacity(0.7)

        self.setAutoFillBackground(True)

        grip_size = 5
        self.grip = QSizeGrip(self)
        self.grip.resize(grip_size, grip_size)
        self.grip.setVisible(True)

        self.is_cycling_from_main_color = True

        self.use_saved_window_geometry()

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

        self._color_main = QColor("grey")

        self.color_animation = QPropertyAnimation(self, b"color")

    # # # # # # # #   QT QWidget overrides

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
            if self.run_on_click is not None:
                logger.info("Glowbox clicked!  Running: %s", self.run_on_click)
                self.run_on_click()
            else:
                logger.info("Glowbox clicked!")

            # TODO Don't close here.  We'll let the state machine (or whatever) handle that.
            self.close_and_save_geometry()
        self.is_moving = False

    # TODO Move the glowbox context menu creation to the main program.
    #  That way we can add as many entries as we want without having to
    #  account for everyone we might want to create in this module.

    # pylint: disable=invalid-name
    # def contextMenuEvent(self, ev):
    #     close_action = QAction("Close program", self)
    #     close_action.triggered.connect(self.close_and_save_geometry)
    #
    #     context = QMenu(self)
    #     context.addAction(close_action)
    #     context.exec(ev.globalPos())

    # # # # # # # #   Changing the color

    def set_main_color(self, color=None):
        if color is not None:
            self._color_main = color
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(self._color_main))
        self.setPalette(palette)

    def transition_to_color(self, transition, on_transition_done=None):
        # TODO If a person really wants to transition the color when the window
        #  is hidden, I could add an option for that here.
        if self.isVisible():
            logger.debug("Transitioning color to %s", transition)
            self.color_animation.setEndValue(QColor(transition["new_color"]))
            self.color_animation.setDuration(transition["duration"])
            # TODO Do I want to change the default easing curve?
            default_easing_curve = QEasingCurve.InOutSine
            if "easing curve" in transition:
                self.color_animation.setEasingCurve(transition["easing curve"])
            else:
                self.color_animation.setEasingCurve(default_easing_curve)
            self.color_animation.start()
            if on_transition_done:
                try:
                    self.color_animation.finished.disconnect()
                except RuntimeError as e:
                    logger.info(
                        # pylint: disable=line-too-long
                        "%s -- There was probably nothing previously connected to the animation finishing, and probably nothing to worry about.",
                        e,
                    )
                self.color_animation.finished.connect(on_transition_done)

    def transition_color_over_iterable(self, transitions, run_on_completion):
        def handle_next_transition():
            try:
                self.transition_to_color(
                    next(transitions), handle_next_transition
                )
            except StopIteration:
                # We don't want the run_on_completion event to run if the
                #  window has already been clicked and hidden.
                # TODO Is there a better way to handle this?
                if not self.isHidden():
                    if run_on_completion:
                        run_on_completion()

        handle_next_transition()

    # # # # # # # #   Window geometry

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
                shutil.copy2(filename, filename + ".backup")
            except FileNotFoundError as e2:
                logger.info("Could not make a backup  (%s)", e2)
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


# pylint: disable=too-many-arguments, useless-return
def intervals_decreasing_over_total_time(
    rough_starting_interval,
    ending_interval,
    total_time,
    main_color,
    secondary_color,
    to_nearest_even_number=True,
):
    logger.debug(
        "Starting intervals_decreasing_over_total_time(%s, %s, %s)",
        rough_starting_interval,
        ending_interval,
        total_time,
    )

    unrounded_number_of_intervals = (
        2 * total_time / (rough_starting_interval + ending_interval)
    )
    logger.debug(
        "Approximate number of intervals: %s", unrounded_number_of_intervals
    )

    if to_nearest_even_number:
        final_number_of_intervals = int(
            nearest_even(unrounded_number_of_intervals)
        )
    logger.debug("Final number of intervals: %s", final_number_of_intervals)

    new_starting_interval = (
        2 * total_time / final_number_of_intervals
    ) - ending_interval
    logger.debug("New starting interval: %s", new_starting_interval)

    for i in range(final_number_of_intervals):
        slope = (
            ending_interval - new_starting_interval
        ) / final_number_of_intervals
        # We add 0.5, because we want to get the timing of the interval
        #  from the slope of the equation at the middle of the interval.
        #  (Since the slope is linear, you can the whole time taken by
        #  the interval is the time at the midpoint of the interval...
        # I dunno how exactly to say what I was saying there.  Imma come
        #  back to it.  TODO.
        next_duration = new_starting_interval + ((i + 0.5) * slope)
        next_duration *= 1_000
        next_duration = int(next_duration)

        # logger.info("i: %s", i)
        if i % 2 == 0:
            color = secondary_color
        else:
            color = main_color

        yield {"new_color": color, "duration": next_duration}
        # logger.info(i, "\t", next_duration, "\t", sum(intervals)/1_000)

    # I'm leaving the `return` statement here to make clear that the iterator
    #  should end at this point.
    return


def steady_pulse(interval, main_color, secondary_color):
    on_main_color = True
    while True:
        if on_main_color:
            color = secondary_color
        else:
            color = main_color
        on_main_color = not on_main_color

        yield {"new_color": color, "duration": interval}
