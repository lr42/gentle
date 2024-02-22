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


class BaseBreakScreen(QWidget):
    def __init__(self, timeout_length, run_on_completion):
        super().__init__()

        self._run_on_completion = run_on_completion

        ################  Initialize the countdown timer
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self._timeout_length = timeout_length

        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.FramelessWindowHint, True)

        ################  Set dark background and light text
        # TODO Make this customizable
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("black"))
        palette.setColor(QPalette.WindowText, QColor("lightGray"))
        self.setPalette(palette)

    def update_countdown(self):
        self.remaining_time = self.remaining_time.addSecs(-1)
        if self.remaining_time == QTime(0, 0, 0):
            self.countdown_timer.stop()
            self._run_on_completion()

    def showEvent(self, event):
        """Start the timer when the window is shown."""
        self.remaining_time = QTime(0, self._timeout_length // 60, self._timeout_length % 60)
        self.countdown_timer.start(1_000)  # Update every second


class ShortBreakScreen(BaseBreakScreen):
    def __init__(self, timeout_length, run_on_completion):
        super().__init__(timeout_length, run_on_completion)

        ################  Create the layout
        layout = QVBoxLayout()

        self.big_text_label = QLabel()
        self.big_text_label.setAlignment(Qt.AlignCenter)
        self.big_text_label.setWordWrap(True)
        font = self.big_text_label.font()
        # TODO She's a witch!  Burn her!  She uses magic numbers!
        font.setPointSize(128)  # Set font size
        self.big_text_label.setFont(font)
        self.big_text_label.setText("Look at something far away.")
        layout.addWidget(self.big_text_label)

        self.setLayout(layout)


class LongreakScreen(BaseBreakScreen):
    def __init__(self, timeout_length, run_on_completion):
        super().__init__(timeout_length, run_on_completion)

        ################  Create the layout
        layout = QVBoxLayout()

        self.countdown_label = QLabel()
        self.countdown_label.setAlignment(Qt.AlignCenter)
        font = self.countdown_label.font()
        # TODO She's a witch!  Burn her!  She uses magic numbers!
        font.setPointSize(128)  # Set font size
        self.countdown_label.setFont(font)
        layout.addWidget(self.countdown_label)

        close_button = QPushButton("Let me get back to work!")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def update_countdown(self):
        super().update_countdown()
        self.countdown_label.setText(self.remaining_time.toString())


