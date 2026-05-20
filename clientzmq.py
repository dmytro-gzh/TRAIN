# ---- nano_a.py (sender/client) ----
import zmq
import time

ctx = zmq.Context()

# PUSH socket — sends detections to Nano B
push = ctx.socket(zmq.PUSH)
push.connect("tcp://10.13.196.94:5555")  # Fixed: removed markdown link wrapping

# PULL socket — receives commands from Nano B
pull = ctx.socket(zmq.PULL)
pull.bind("tcp://*:5556")

poller = zmq.Poller()
poller.register(pull, zmq.POLLIN)


def send_data():
    """Send a fixed detection message with the current timestamp."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"human detected | {timestamp}"
    push.send_string(message)
    print(f"Sent: {message}")


def receive_data():
    """Poll for incoming commands and print plain text to console."""
    events = dict(poller.poll(timeout=10))
    if pull in events:
        msg = pull.recv_string()  # receive as plain text
        print(msg)


# --- Main loop ---
while True:
    send_data()
    receive_data()
    time.sleep(1)  # adjust rate as needed
