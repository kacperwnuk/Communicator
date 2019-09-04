import socket
import selectors
import threading
import configuration as config

DATA_FUNCTION = 'data_fun'
CLIENT_INFO = 'client_info'


class Server:
    def __init__(self):
        self.socket = None
        self.is_running = True
        self.clients = []
        self.prepare_server_socket()
        self.selector = selectors.DefaultSelector()

    def disconnect_all_clients(self):
        for client in self.clients:
            self.selector.unregister(client)
            client.sock.close()
        self.clients.clear()

    def close(self):
        self.socket.close()

    def prepare_server_socket(self):
        """
           Creates socket and sets it to listen
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((config.HOST, config.PORT))
        self.socket.listen(5)
        self.socket.setblocking(False)

    def accept(self, key, _):
        """
            Accepts new clients and adds them to selector
            :param key: info from event returned by selector
            :param _:
        """
        sock = key.fileobj

        conn, addr = sock.accept()
        conn.setblocking(False)
        client = Client(conn)
        data = {
            DATA_FUNCTION: self.manage_data,
            CLIENT_INFO: client
        }
        self.selector.register(conn, selectors.EVENT_READ, data=data)
        self.clients.append(client)

    def send_to_all(self, message):
        """
            Sending message to all clients online
            :param message: message to be sent
        """
        for client in self.clients:
            client.sock.send(bytes("{:04d}".format(len(message)), config.ENCODING))
            client.sock.send(message)

    def manage_data(self, key, mask):
        """
            Reads and writes data from sockets
            :param key: socket info from selector
            :param mask: determines if data is sent or downloaded
        """
        sock = key.fileobj
        client = key.data[CLIENT_INFO]

        if mask & selectors.EVENT_READ:
            if client.sending_header:
                try:
                    header = int(sock.recv(config.HEADER_SIZE))
                    client.message_size = header
                    client.sending_header = False
                except ValueError:
                    print("Closing connection")
                    self.clients.remove(client)
                    self.selector.unregister(sock)
                    sock.close()
                    self.send_to_all(bytes(f"{client.nickname} has left the chat", config.ENCODING))
            else:
                message = sock.recv(client.message_size)
                client.message_out_buffer += message
                client.message_size -= len(message)
                if client.message_size == 0:
                    if client.nickname:
                        message = bytes(f"{client.nickname}: ", config.ENCODING) + client.message_out_buffer
                        self.send_to_all(message)
                    else:
                        client.nickname = client.message_out_buffer.decode(config.ENCODING)
                    client.reset_status()


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
        self.message_size = config.HEADER_SIZE
        self.message_out_buffer = b''

    def reset_status(self):
        self.sending_header = True
        self.message_size = config.HEADER_SIZE
        self.message_out_buffer = b''


def console(server):
    """
        Thread that enables quitting server
        :param server: server supported by console
    """
    while server.is_running:
        command = input("Type q to quit server: ")
        if command == 'q':
            server.is_running = False
            break
        print(command)


def run(server):
    """
        Runs server with console.
        :param server: server that is going to be started
    """
    console_thread = threading.Thread(target=console, args=[server])
    console_thread.start()

    data = {
        DATA_FUNCTION: server.accept
    }
    server.selector.register(server.socket, selectors.EVENT_READ, data=data)

    while server.is_running:
        event = server.selector.select(timeout=None)
        for key, mask in event:
            key.data[DATA_FUNCTION](key, mask, server.clients)

    server.disconnect_all_clients()
    server.close()


if __name__ == '__main__':
    server = Server()
    run(server)
