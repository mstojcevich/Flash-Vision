import socket


msg = 'Hello world!'
host = '0.0.0.0'
port = 8622

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))  # TODO allow user-defined port (maybe)
s.send(str(len(msg)).ljust(16))
s.send(msg)