# coding: utf-8

import sys
from PySide6.QtWidgets import (
    QVBoxLayout,
    QApplication,
    QWizard,
    QWizardPage,
    QLabel,
)


class IntroWizard(QWizard):
    def __init__(self):
        super().__init__()

        p1 = QWizardPage()
        v1 = QVBoxLayout()
        l1 = QLabel()
        l1.setText("<big>Welcome to Gentle Break Reminder!</big>")
        v1.addWidget(l1)
        p1.setLayout(v1)
        self.addPage(p1)

        p2 = QWizardPage()
        v2 = QVBoxLayout()
        l2 = QLabel()
        l2.setText(
            "Gentle Break Reminder will remind you to take breaks in a very gentle way.  This will be a quick introduction to how it works."
        )
        l2.setWordWrap(True)
        v2.addWidget(l2)
        p2.setLayout(v2)
        self.addPage(p2)


if __name__ == "__main__":
    app = QApplication()
    w = IntroWizard()
    w.show()
    sys.exit(app.exec())
