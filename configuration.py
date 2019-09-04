"""
    Messages between server and client:
    HEADER_SIZE: size of message header
    message body has size specified in header
    Example:
    HEADER -> 0003
    MSG_BODY -> abc
    ENCODING: type of encoding
"""

HEADER_SIZE = 4
ENCODING = "utf-8"
HOST = '127.0.0.1'
PORT = 6001
