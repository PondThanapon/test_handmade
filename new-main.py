import cv2
import json
import math
import socket
import struct
import mediapipe as mp
import numpy as np

# =========================
# CONFIG
# =========================
TCP_IP = "0.0.0.0"
TCP_PORT = 5058

UDP_IP = "127.0.0.1"
UDP_PORT = 5052

MAX_HANDS = 2

# =========================
# UDP
# =========================
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# =========================
# TCP (Unity → Python)
# =========================
tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_sock.bind((TCP_IP, TCP_PORT))
tcp_sock.listen(1)

print("Waiting for Unity camera stream...")
conn, addr = tcp_sock.accept()
print("Connected from", addr)

# =========================
# MediaPipe
# =========================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=MAX_HANDS,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

# =========================
# Utils
# =========================
def distance(a, b):
    return math.sqrt(
        (a.x - b.x) ** 2 +
        (a.y - b.y) ** 2
    )

def calc_pinch(hand):
    thumb = hand.landmark[4]
    index = hand.landmark[8]
    d = distance(thumb, index)
    return max(0.0, min(1.0, 1.0 - d * 6))

def recv_all(sock, size):
    data = b''
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None
        data += packet
    return data

# =========================
# Main Loop
# =========================
while True:
    # ---- Receive JPG size ----
    raw_len = recv_all(conn, 4)
    if not raw_len:
        break

    frame_len = struct.unpack("<I", raw_len)[0]

    # ---- Receive JPG ----
    jpg_data = recv_all(conn, frame_len)
    if jpg_data is None:
        break

    # ---- Decode image ----
    frame = cv2.imdecode(
        np.frombuffer(jpg_data, np.uint8),
        cv2.IMREAD_COLOR
    )

    if frame is None:
        continue

    h, w, _ = frame.shape

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    left = None
    right = None

    if results.multi_hand_landmarks and results.multi_handedness:
        for i, hand in enumerate(results.multi_hand_landmarks):
            handed = results.multi_handedness[i].classification[0].label

            index_tip = hand.landmark[8]
            pinch = calc_pinch(hand)

            data = {
                "x": int(index_tip.x * w),
                "y": int(index_tip.y * h),
                "pinch": round(pinch, 3)
            }

            if handed == "Left":
                left = data
            else:
                right = data

    packet = {
        "left": left,
        "right": right
    }

    udp_sock.sendto(
        json.dumps(packet).encode("utf-8"),
        (UDP_IP, UDP_PORT)
    )
# =========================
# Cleanup
# =========================
conn.close()
tcp_sock.close()
udp_sock.close()