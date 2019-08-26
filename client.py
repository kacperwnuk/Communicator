import PyQt5.QtWidgets as qt
from PyQt5 import QtCore
import socket
import selectors
import threading
import queue
import configuration as config


class LoginWindow(qt.QWidget):
    """
        Window showed when application connected with server successfully.
    """

    switch_window = QtCore.pyqtSignal()

    def __init__(self, message_buffer, parent=None):
        super().__init__(parent)
        self.message_buffer = message_buffer

        self.resize(400, 300)
        self.setWindowTitle("Chat room login window")
        layout = qt.QVBoxLayout()

        self.login_bar = qt.QLineEdit()
        self.login_bar.setPlaceholderText('Login')

        self.ready_button = qt.QPushButton('Join chat room')
        self.ready_button.clicked.connect(self.button_clicked)

        layout.addWidget(self.login_bar)
        layout.addWidget(self.ready_button)

        self.setLayout(layout)

    def button_clicked(self):
        login = self.login_bar.text()
        if not login:
            self.show_error_dialog()
        else:
            self.message_buffer.put(self.login_bar.text())
            self.switch_window.emit()

    @staticmethod
    def show_error_dialog():
        msg = qt.QMessageBox()
        msg.setIcon(qt.QMessageBox.Information)
        msg.setText("You need to pass login before start!")
        msg.setWindowTitle("Error!")
        msg.exec_()


class MainWindow(qt.QWidget):
    """
        Main window of chat room, user can send and read messages there.
    """
    def __init__(self, out_queue, in_queue, parent=None):
        super().__init__(parent)
        self.initialize()
        self.message_out_buffer = out_queue
        self.window_is_open = True
        self.chat_thread = threading.Thread(target=self.wait_for_message, args=[in_queue])
        self.chat_thread.start()

    def initialize(self):
        layout = qt.QVBoxLayout()
        self.setWindowTitle("Chat room")

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
        message = self.text_panel.text()
        self.message_out_buffer.put(message)

    def add_message(self, message):
        self.message_browser.append(message)

    def closeEvent(self, event):
        self.window_is_open = False
        print(self.window_is_open)
        super().closeEvent(event)

    def wait_for_message(self, message_in_buffer):
        while self.window_is_open:
            try:
                message = message_in_buffer.get(timeout=10)
                print(message)
                self.add_message(message)
            except queue.Empty:
                pass


class Controller:
    """
        Supposed to switch windows after user interaction
    """
    def __init__(self, in_queue, out_queue):
        self.message_out_buffer = out_queue
        self.message_in_buffer = in_queue
        self.login_window = None
        self.main_window = None
        self.show_login()

    def show_login(self):
        self.login_window = LoginWindow(self.message_out_buffer)
        self.login_window.switch_window.connect(self.show_main)
        self.login_window.show()

    def show_main(self):
        self.main_window = MainWindow(self.message_out_buffer, self.message_in_buffer)
        self.login_window.close()
        self.main_window.show()

    def update_main_window(self, message):
        self.main_window.add_message(message)


class ConnectionHandler:
    """
        Creates socket and connects with server. Showing error window when connection with server
        cannot be established.
    """
    def __init__(self, server_adr):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = server_adr
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.s, events=selectors.EVENT_READ | selectors.EVENT_WRITE, data=None)

    def connect(self):
        if self.s.connect_ex(self.server_address) != 0:
            self.show_connection_error()

    def show_connection_error(self):
        msg = qt.QMessageBox()
        msg.setWindowTitle("Connection problem")
        msg.setIcon(qt.QMessageBox.Critical)
        msg.setText('Program was unable to connect with server')
        msg.setStandardButtons(qt.QMessageBox.Retry)
        msg.buttonClicked.connect(self.connect)
        msg.exec_()

    def close(self):
        self.selector.unregister(self.s)
        self.s.close()


class MessageHandler(threading.Thread):
    """
        Thread responsible for sending and downloading messages from server.
        message_out_buffer: stores messages to be sent
        message_in_buffer: stores messages to be shown in user window
        client_is_running: flag storing application status
    """
    def __init__(self, in_queue, out_queue, client_running, selector):
        super().__init__(target=self.handle_messages)
        self.message_out_buffer = out_queue
        self.message_in_buffer = in_queue
        self.message_size = config.HEADER_SIZE
        self.client_is_running = client_running
        self.selector = selector

    def handle_messages(self):
        waiting_for_header = True
        while self.client_is_running[0]:
            event = self.selector.select(timeout=None)
            for key, mask in event:
                sock = key.fileobj
                if mask & selectors.EVENT_READ:
                    if waiting_for_header:
                        self.message_size = int(sock.recv(self.message_size))
                        waiting_for_header = False
                    else:
                        message = sock.recv(self.message_size)
                        self.message_in_buffer.put(message.decode(config.ENCODING))
                        self.message_size = config.HEADER_SIZE
                        waiting_for_header = True

                if mask & selectors.EVENT_WRITE:
                    if not self.message_out_buffer.empty():
                        message = self.message_out_buffer.get()
                        sock.send(bytes("{:04d}".format(len(message)), config.ENCODING))
                        sock.send(bytes(message, config.ENCODING))


def run():
    in_queue = queue.Queue()
    out_queue = queue.Queue()

    client_running = [True]

    server_adr = (config.HOST, config.PORT)
    app = qt.QApplication([])

    connection_handler = ConnectionHandler(server_adr)
    connection_handler.connect()

    controller = Controller(in_queue, out_queue)
    message_handler = MessageHandler(in_queue, out_queue, client_running, connection_handler.selector)

    message_handler.start()
    controller.show_login()
    app.exec_()

    client_running[0] = False
    message_handler.join()

    connection_handler.close()


if __name__ == "__main__":
    run()
