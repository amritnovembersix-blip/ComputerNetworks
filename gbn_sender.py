import os, random, socket, struct, sys, time

# ---------------- settings ----------------
FILE = sys.argv[1] if len(sys.argv) > 1 else "test.txt"   # file to send
HOST = "127.0.0.1"
PORT = 9000
CHUNK = 1024          # payload bytes per packet
WINDOW = 5            # N: max unacknowledged packets in flight
TIMEOUT = 0.5         # seconds before we resend the whole window
MAX_RETRIES = 20      # give up after this many timeouts with no progress
LOSS_RATE = 0.2       # simulate dropping 20% of outgoing packets (0 = off)

# ---------------- packet format ----------------
# header = 1 byte type + 4 byte sequence number, then payload
HDR = struct.Struct("!BI")
META, DATA, FIN, ACK = 0, 1, 2, 3


def make(ptype, seq, payload=b""):
    return HDR.pack(ptype, seq) + payload


def unreliable_send(sock, pkt, addr):
    """sendto() that randomly 'loses' packets so we can watch Go-Back-N work."""
    if random.random() >= LOSS_RATE:
        sock.sendto(pkt, addr)


# ---------------- build every packet up front ----------------
size = os.path.getsize(FILE)
packets = [make(META, 0, f"{os.path.basename(FILE)}|{size}".encode())]
with open(FILE, "rb") as f:
    while chunk := f.read(CHUNK):
        packets.append(make(DATA, len(packets), chunk))
packets.append(make(FIN, len(packets)))
total = len(packets)

addr = (HOST, PORT)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

base = 0          # oldest unacknowledged packet
next_seq = 0      # next packet to send for the first time
retries = 0
sent = resent = 0
timer_start = None
start_time = time.time()

print(f"Sending '{FILE}' ({size} bytes) as {total} packets, window={WINDOW}, loss={LOSS_RATE:.0%}")

while base < total:
    # 1) fill the window
    while next_seq < base + WINDOW and next_seq < total:
        unreliable_send(sock, packets[next_seq], addr)
        sent += 1
        print(f"  send seq={next_seq}   [base={base}]")
        if base == next_seq:
            timer_start = time.time()      # timer runs for the oldest unacked packet
        next_seq += 1

    # 2) wait for an ACK, but only until the timer expires
    remaining = TIMEOUT - (time.time() - timer_start)
    sock.settimeout(max(remaining, 0.001))
    try:
        data, _ = sock.recvfrom(2048)
        if len(data) < HDR.size:
            continue
        ptype, ack = HDR.unpack(data[:HDR.size])
        # ACK n is cumulative: "I have everything below n, send me n next"
        if ptype == ACK and ack > base:
            print(f"  ACK  {ack}  -> window slides {base} -> {ack}")
            base = ack
            retries = 0
            timer_start = time.time()
    except socket.timeout:
        retries += 1
        if retries > MAX_RETRIES:
            sys.exit("Giving up: receiver is not responding.")
        print(f"  TIMEOUT -> go back to seq={base}, resend {base}..{next_seq - 1}")
        for seq in range(base, next_seq):
            unreliable_send(sock, packets[seq], addr)
            resent += 1
        timer_start = time.time()

elapsed = time.time() - start_time
print(f"Done: '{FILE}' delivered in {elapsed:.2f}s | {total} packets, "
      f"{sent} first transmissions, {resent} retransmissions")