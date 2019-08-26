import PyQt5.QtWidgets as qt
from PyQt5 import QtCore
import socket
import selectors
import threading
import queue

HOST = '127.0.0.1'
PORT = 6001
sel = selectors.DefaultSelector()
sem = threading.Semaphore()
HEADER_SIZE = 4
ENCODING = "utf-8"


class LoginWindow(qt.QWidget):
    switch_window = QtCore.pyqtSignal()

    def __init__(self, message_buffer, parent=None):
        super().__init__(parent)
        self.message_buffer = message_buffer
        self.initialize()

    def initialize(self):
        self.resize(400, 300)
        self.setWindowTitle("Chat room login window")
        layout = qt.QVBoxLayout()

        self.login_bar = qt.QLineEdit()
        self.login_bar.setPlaceholderText('Login')

        ready_button = qt.QPushButton('Join chat room')
        ready_button.clicked.connect(self.button_clicked)

        layout.addWidget(self.login_bar)
        layout.addWidget(ready_button)

        self.setLayout(layout)

    def button_clicked(self):
        self.message_buffer.put(bytes(self.login_bar.text(), ENCODING))
        # self.switch_window.emit()


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

    def add_message(self, message):
        self.message_browser.append(message)


class Controller:
    def __init__(self, in_queue, out_queue):
        self.message_in_buffer = in_queue
        self.message_out_buffer = out_queue
        self.show_login()

    def show_login(self):
        self.login_window = LoginWindow(self.message_out_buffer)
        self.login_window.switch_window.connect(self.show_main)
        self.login_window.show()

    def show_main(self):
        self.main_window = MainWindow()
        self.login_window.close()
        self.main_window.show()

    def update_main_window(self, message):
        self.main_window.add_message(message)


def run():
    in_queue = queue.Queue()
    out_queue = queue.Queue()

    client_running = [True]

    message_handler = MessageHandler(in_queue, out_queue, client_running)

    server_adr = (HOST, PORT)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(s.connect_ex(server_adr))
    s.setblocking(False)

    app = qt.QApplication([])
    controller = Controller(in_queue, out_queue)
    sel.register(s, events=selectors.EVENT_READ | selectors.EVENT_WRITE, data=None)

    message_handler.start()
    controller.show_login()
    app.exec_()

    client_running[0] = False
    message_handler.join()
    s.close()


class MessageHandler(threading.Thread):
    def __init__(self, in_queue, out_queue, client_running):
        super().__init__(target=self.handle_messages)
        self.message_out_buffer = out_queue
        self.message_in_buffer = in_queue
        self.message_size = HEADER_SIZE
        self.client_is_running = client_running

    def handle_messages(self):
        waiting_for_header = True
        while self.client_is_running[0]:
            event = sel.select(timeout=None)
            for key, mask in event:
                sock = key.fileobj
                if mask & selectors.EVENT_READ:
                    if waiting_for_header:
                        self.message_size = int(sock.recv(self.message_size))
                        waiting_for_header = False
                    else:
                        message = sock.recv(self.message_size)
                        print(message)
                        self.message_in_buffer.put(message)
                        self.message_size = HEADER_SIZE
                        waiting_for_header = True

                if mask & selectors.EVENT_WRITE:
                    if not self.message_out_buffer.empty():
                        message = self.message_out_buffer.get()
                        sock.send(bytes("{:04d}".format(len(message)), ENCODING))
                        sock.send(message)


if __name__ == "__main__":
    run()
