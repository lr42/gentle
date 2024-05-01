# coding: utf-8

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

        self._add_page("<big>Welcome to Gentle Break Reminder!</big>")

        self._add_page(
            "Gentle Break Reminder will remind you to take breaks in a very gentle way.  This will be a quick introduction to how it works."
        )

    def _add_page(self, text):
        p = QWizardPage()
        v = QVBoxLayout()
        l = QLabel()
        l.setWordWrap(True)
        l.setText(text)
        v.addWidget(l)
        p.setLayout(v)
        self.addPage(p)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication()
    w = IntroWizard()
    w.show()
    sys.exit(app.exec())
