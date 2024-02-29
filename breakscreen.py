from PySide6.QtCore import (
    Qt,
    QPropertyAnimation,
    Property,
    QEasingCurve,
    QTimer,
    QTime,
)
from PySide6.QtGui import QAction, QColor, QPalette, QScreen, QIcon, QFontMetrics, QTextOption
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
    QStackedLayout,
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
        self._remaining_time = self._remaining_time.addSecs(-1)
        if self._remaining_time == QTime(0, 0, 0):
            self.countdown_timer.stop()
            self._run_on_completion()

    def showEvent(self, event):
        """Start the timer when the window is shown."""
        self._remaining_time = QTime(0, self._timeout_length // 60, self._timeout_length % 60)
        self.countdown_timer.start(1_000)

    def hideEvent(self, event):
        self.countdown_timer.stop()


class ShortBreakScreen(BaseBreakScreen):
    def __init__(self, timeout_length, run_on_completion):
        super().__init__(timeout_length, run_on_completion)

        ################  Create the layout
        layout = QVBoxLayout()

        self.big_text_label = QLabel()
        self.big_text_label.setAlignment(Qt.AlignCenter)
        self.big_text_label.setWordWrap(True)

        self.big_text_label.setText("Look at something <i>far</i> away.")

        font = self.big_text_label.font()
        # TODO She's a witch!  Burn her!  She uses magic numbers!
        font.setPointSize(96)  # Set font size
        self.big_text_label.setFont(font)
        layout.addWidget(self.big_text_label)

        self.setLayout(layout)


class LongBreakScreen(BaseBreakScreen):
    def __init__(self, timeout_length, run_on_completion, run_on_finish, run_on_skip=None):
        super().__init__(timeout_length, run_on_completion)

        ################  Create the countdown layout
        self.countdown_layout_widget = QWidget()
        self.countdown_layout = QVBoxLayout()

        self.countdown_label = QLabel()
        self.countdown_label.setAlignment(Qt.AlignCenter)
        font = self.countdown_label.font()
        # TODO She's a witch!  Burn her!  She uses magic numbers!
        font.setPointSize(96)
        self.countdown_label.setFont(font)
        self._remaining_time = QTime(0, self._timeout_length // 60, self._timeout_length % 60)
        self.countdown_label.setText(self._remaining_time.toString())
        self.countdown_layout.addWidget(self.countdown_label)

        if run_on_skip is not None:
            skip_button = QPushButton("Skip this break.  :-(")
            skip_button.clicked.connect(run_on_skip)
            skip_button.clicked.connect(self.hide)
            self.countdown_layout.addWidget(skip_button)

        self.countdown_layout_widget.setLayout(self.countdown_layout)

        ################  Create the finished layout
        self.finished_layout_widget = QWidget()
        self.finished_layout = QVBoxLayout()

        self.finished_label = QLabel()
        self.finished_label.setAlignment(Qt.AlignCenter)
        font = self.finished_label.font()
        # TODO She's a witch!  Burn her!  She uses magic numbers!
        font.setPointSize(96)
        self.finished_label.setFont(font)
        self.finished_label.setText("Finished!")
        self.finished_layout.addWidget(self.finished_label)

        finish_button = QPushButton("Let me get back to work!")
        finish_button.clicked.connect(run_on_finish)
        finish_button.clicked.connect(self.hide)
        self.finished_layout.addWidget(finish_button)

        self.finished_layout_widget.setLayout(self.finished_layout)

        ################  Stack the layouts so we can switch between them
        self.stacked_layout = QStackedLayout()
        self.stacked_layout.addWidget(self.countdown_layout_widget)
        self.stacked_layout.addWidget(self.finished_layout_widget)

        self.setLayout(self.stacked_layout)

    def update_countdown(self):
        super().update_countdown()
        self.countdown_label.setText(self._remaining_time.toString())

    def set_layout_to_countdown(self):
        self.stacked_layout.setCurrentIndex(0)

    def set_layout_to_finished(self):
        self.stacked_layout.setCurrentIndex(1)

