import os, random, socket, struct

# ---------------- settings ----------------
PORT = 9000
LOSS_RATE = 0.2        # simulate dropping 20% of outgoing ACKs (0 = off)
IDLE_TIMEOUT = 15      # give up if the sender goes silent this long
LINGER = 2             # after FIN, stay up this long to re-ACK lost final ACKs

HDR = struct.Struct("!BI")
META, DATA, FIN, ACK = 0, 1, 2, 3


def send_ack(sock, addr, expected):
    """Cumulative ACK: 'I have received everything below `expected`'."""
    if random.random() >= LOSS_RATE:
        sock.sendto(HDR.pack(ACK, expected), addr)


os.makedirs("received", exist_ok=True)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))
print(f"GBN receiver listening on UDP port {PORT} ...")

expected = 0          # the ONLY sequence number we will accept next
sender = None
out = None
name, size, got = None, 0, 0
finished = False
sock.settimeout(IDLE_TIMEOUT)

while True:
    try:
        data, addr = sock.recvfrom(2048)
    except socket.timeout:
        if finished:
            break                      # lingered long enough, all done
        print("Timed out waiting for sender.")
        break
    if len(data) < HDR.size:
        continue
    if sender is None:
        sender = addr                  # lock on to the first sender
    elif addr != sender:
        continue

    ptype, seq = HDR.unpack(data[:HDR.size])
    payload = data[HDR.size:]

    if seq == expected:
        # in order: accept it
        if ptype == META:
            name, size = payload.decode().split("|")
            name, size = os.path.basename(name), int(size)
            out = open(os.path.join("received", name), "wb")
            print(f"Receiving '{name}' ({size} bytes) from {addr}")
        elif ptype == DATA:
            out.write(payload)
            got += len(payload)
        elif ptype == FIN:
            out.close()
            finished = True
            sock.settimeout(LINGER)
            print(f"Saved received/{name}: {got}/{size} bytes")
            print("Transfer complete." if got == size else "WARNING: size mismatch.")
        print(f"  accept  seq={seq}")
        expected += 1
    else:
        # out of order or duplicate: DISCARD it (no buffering in Go-Back-N)
        print(f"  discard seq={seq} (expected {expected})")

    # always ACK with the next in-order sequence number we are waiting for
    send_ack(sock, addr, expected)