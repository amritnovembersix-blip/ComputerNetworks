import os, socket, time

FILE = "test.txt"      # file to send
HOST = "127.0.0.1"     # same computer
PORT = 9000

addr = (HOST, PORT)
size = os.path.getsize(FILE)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.sendto(f"START|{os.path.basename(FILE)}|{size}".encode(), addr)
time.sleep(0.1)

packets = 0
with open(FILE, "rb") as f:
    while chunk := f.read(1024):
        sock.sendto(chunk, addr)
        packets += 1
        time.sleep(0.0005)

for _ in range(3):
    sock.sendto(b"END", addr)
    time.sleep(0.05)
print(f"Sent '{FILE}': {size} bytes in {packets} packets")