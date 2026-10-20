import os, socket

PORT = 9000
os.makedirs("received", exist_ok=True)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))
print(f"Receiver listening on UDP port {PORT} ...")

while True:
    data, addr = sock.recvfrom(2048)
    if data.startswith(b"START|"):
        _, name, size = data.decode().split("|")
        name, size = os.path.basename(name), int(size)
        break
print(f"Receiving '{name}' ({size} bytes) from {addr}")

got = 0
sock.settimeout(5)
with open(os.path.join("received", name), "wb") as f:
    try:
        while True:
            data, _ = sock.recvfrom(2048)
            if data == b"END":
                break
            f.write(data)
            got += len(data)
    except socket.timeout:
        print("Timed out waiting for data.")

print(f"Saved received/{name}: {got}/{size} bytes")
print("Transfer complete." if got == size else "WARNING: some bytes were lost (plain UDP).")