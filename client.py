import PyQt5.QtWidgets as qt
from PyQt5 import QtCore


class LoginWindow(qt.QWidget):
    switch_window = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initialize()

    def initialize(self):
        self.resize(400, 300)
        self.setWindowTitle("Chat room login window")
        layout = qt.QVBoxLayout()

        login_bar = qt.QLineEdit()
        login_bar.setPlaceholderText('Login')

        ready_button = qt.QPushButton('Join chat room')
        ready_button.clicked.connect(self.button_clicked)

        layout.addWidget(login_bar)
        layout.addWidget(ready_button)

        self.setLayout(layout)

    def button_clicked(self):
        self.switch_window.emit()


class MainWindow(qt.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initialize()

    def initialize(self):
        layout = qt.QVBoxLayout()

        self.message_browser = qt.QTextBrowser()

        self.text_panel = qt.QLineEdit()
        self.text_panel.setPlaceholderText("Your message")

        self.message_button = qt.QPushButton('Send message')
        self.message_button.clicked.connect(self.send_message)

        layout.addWidget(self.message_browser)
        layout.addWidget(self.text_panel)
        layout.addWidget(self.message_button)

        self.setLayout(layout)

    def send_message(self):
        self.message_browser.append(self.text_panel.text())


class Controller:
    def __init__(self):
        self.show_login()

    def show_login(self):
        self.login_window = LoginWindow()
        self.login_window.switch_window.connect(self.show_main)
        self.login_window.show()

    def show_main(self):
        self.main_window = MainWindow()
        self.login_window.close()
        self.main_window.show()


def run():
    app = qt.QApplication([])
    controller = Controller()
    controller.show_login()
    app.exec_()


if __name__ == "__main__":
    run()
