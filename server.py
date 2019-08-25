import socket
import selectors
import threading

HOST = '127.0.0.1'
PORT = 6000
sel = selectors.DefaultSelector()
DATA_FUNCTION = 'data_fun'
CLIENT_INFO = 'client_info'
HEADER_SIZE = 4
ENCODING = "utf-8"


"""
    Messages between server and client:
    4bytes header with size of body
    message body
"""


def accept(key, _, clients):
    sock = key.fileobj

    conn, addr = sock.accept()
    print(f"Accepted {conn} {addr}")
    conn.setblocking(False)
    client = Client(conn)
    print(client.nickname)
    data = {
        DATA_FUNCTION: manage_data,
        CLIENT_INFO: client
    }
    sel.register(conn, selectors.EVENT_READ, data=data)
    clients.append(client)


def send_to_all(message, clients):
    for client in clients:
        client.sock.send(message)


def manage_data(key, mask, clients: list):
    sock = key.fileobj
    client = key.data[CLIENT_INFO]

    if mask & selectors.EVENT_READ:
        if client.sending_header:
            try:
                header = int(sock.recv(HEADER_SIZE))
                client.message_size = header
                client.sending_header = False
            except ValueError:
                print("Closing connection")
                clients.remove(client)
                sel.unregister(sock)
                sock.close()
        else:
            message = sock.recv(client.message_size)
            client.message_out_buffer += message
            client.message_size -= len(message)
            if client.message_size == 0:
                if client.nickname:
                    message = bytes(f"{client.nickname}: ", ENCODING) + client.message_out_buffer
                    send_to_all(message, clients)
                else:
                    client.nickname = client.message_out_buffer.decode(ENCODING)
                client.reset_status()


def prepare_server_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(5)
    s.setblocking(False)
    return s


def console(server):
    while server.is_running:
        command = input("Type q to quit server: ")
        if command == 'q':
            server.is_running = False
            break
        print(command)


def run(server):
    console_thread = threading.Thread(target=console, args=[server])
    console_thread.start()

    data = {
        DATA_FUNCTION: accept
    }
    sel.register(server.socket, selectors.EVENT_READ, data=data)

    while server.is_running:
        event = sel.select(timeout=None)
        for key, mask in event:
            key.data[DATA_FUNCTION](key, mask, server.clients)

    server.disconnect_all_clients()


class Server:
    def __init__(self):
        self.socket = prepare_server_socket()
        self.is_running = True
        self.clients = []

    def disconnect_all_clients(self):
        for client in self.clients:
            sel.unregister(client)
            client.sock.close()
        self.clients.clear()


class Client:
    """
        Storing basic client info
        sock - socket
        nickname - username
        sending_header - flag used to determine what`s the next step in communication
        message_size - stores amount of bytes that needs to be received
        message_out_buffer - stores message which is going to be sent when collected
    """

    def __init__(self, sock):
        self.sock = sock
        self.nickname = None
        self.sending_header = True
        self.message_size = HEADER_SIZE
        self.message_out_buffer = b''

    def reset_status(self):
        self.sending_header = True
        self.message_size = HEADER_SIZE
        self.message_out_buffer = b''


if __name__ == '__main__':
    server = Server()
    run(server)
