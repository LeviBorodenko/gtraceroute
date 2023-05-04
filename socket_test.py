import socket
import struct
from random import randbytes

HOST = "1.1.1.1"
PORT = 12345
MESSAGE = randbytes(8)
ICMP_PROTO = socket.getprotobyname("icmp")


udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
icmp_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, ICMP_PROTO)

print(MESSAGE)
udp_socket.sendto(MESSAGE, (HOST, PORT))

data, addr = icmp_socket.recvfrom(1024)
icmp_header = data[20:28]
icmp_message = data[-8:]
icmp_type, icmp_code, _, _ = struct.unpack("BBHi", icmp_header)
print(icmp_type, icmp_code, icmp_message)
