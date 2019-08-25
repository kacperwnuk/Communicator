import random
import socket
import selectors

HOST = '127.0.0.1'
PORT = 6000
sel = selectors.DefaultSelector()
DATA_FUNCTION = 'data_fun'
CLIENT_INFO = 'client_info'


def accept(key, _, clients):
    sock = key.fileobj

    conn, addr = sock.accept()
    print(f"Accepted {conn} {addr}")
    conn.setblocking(False)
    client = Client(conn, random.randint(1, 100))
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
        message = sock.recv(1024)
        print(message)
        if not message:
            print("Closing connection")
            clients.remove(client)
            sel.unregister(sock)
            sock.close()
        else:
            message = bytes(f"{client.nickname}: ", "utf-8") + message
            send_to_all(message, clients)


def run():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(5)
    s.setblocking(False)
    data = {
        DATA_FUNCTION: accept
    }
    sel.register(s, selectors.EVENT_READ, data=data)

    clients = []

    while True:
        event = sel.select(timeout=None)
        for key, mask in event:
            key.data[DATA_FUNCTION](key, mask, clients)


class Client:
    def __init__(self, sock, nickname):
        self.sock = sock
        self.nickname = nickname
        self.waiting_for_header = True
        self.message_size = 4


if __name__ == '__main__':
    run()
