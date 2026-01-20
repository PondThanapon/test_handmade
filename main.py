import os

# Reduce noisy MediaPipe/TF native logs (glog). This must run before importing mediapipe.
os.environ.setdefault("GLOG_minloglevel", "2")  # 0=INFO,1=WARNING,2=ERROR,3=FATAL
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import cv2
import json
import math
import time
import socket
import struct

import mediapipe as mp
import numpy as np

try:
    from absl import logging as absl_logging

    absl_logging.set_verbosity(absl_logging.ERROR)
    absl_logging.set_stderrthreshold("error")
except Exception:
    pass

TCP_IP = os.getenv("IMG_BIND_HOST", "0.0.0.0")
TCP_PORT = int(os.getenv("IMG_BIND_PORT", "5055"))

UDP_IP = os.getenv("UDP_IP", os.getenv("UNITY_HOST", "127.0.0.1"))
UDP_PORT = int(os.getenv("UDP_PORT", os.getenv("UNITY_PORT", "5052")))

MAX_HANDS = int(os.getenv("MAX_HANDS", "2"))
DEBUG = os.getenv("DEBUG", "0") == "1"
UDP_APPEND_NEWLINE = os.getenv("UDP_APPEND_NEWLINE", "0") == "1"


# -----------------------------
# MediaPipe Hands
# -----------------------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=MAX_HANDS,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6,
)

udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
tcp_sock.bind((TCP_IP, TCP_PORT))
tcp_sock.listen(1)

print("Waiting for Unity camera stream...")
print(f"Listening TCP on {TCP_IP}:{TCP_PORT}")
print(f"Sending UDP to {UDP_IP}:{UDP_PORT}")


def distance(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def calc_pinch(hand):
    thumb = hand.landmark[4]
    index = hand.landmark[8]
    d = distance(thumb, index)
    return max(0.0, min(1.0, 1.0 - d * 6))


def recv_all(sock, size):
    data = b""
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None
        data += packet
    return data


last_debug_log = 0.0
frames_sent = 0
frames_with_any_hand = 0
frames_with_handedness = 0

while True:
    conn, addr = tcp_sock.accept()
    print("Connected from", addr)

    try:
        while True:
            raw_len = recv_all(conn, 4)
            if not raw_len:
                if DEBUG:
                    print("TCP closed by Unity; waiting for reconnect...")
                break

            frame_len = struct.unpack("<I", raw_len)[0]

            jpg_data = recv_all(conn, frame_len)
            if jpg_data is None:
                if DEBUG:
                    print("TCP stream ended mid-frame; waiting for reconnect...")
                break

            frame = cv2.imdecode(
                np.frombuffer(jpg_data, np.uint8),
                cv2.IMREAD_COLOR,
            )
            if frame is None:
                continue

            h, w, _ = frame.shape

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            if results.multi_hand_landmarks:
                frames_with_any_hand += 1
            if results.multi_handedness:
                frames_with_handedness += 1

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
                        "pinch": round(pinch, 3),
                    }

                    if handed == "Left":
                        left = data
                    else:
                        right = data

            packet = {"left": left, "right": right}
            payload = json.dumps(packet)
            if UDP_APPEND_NEWLINE:
                payload += "\n"
            udp_sock.sendto(payload.encode("utf-8"), (UDP_IP, UDP_PORT))

            if DEBUG:
                frames_sent += 1
                now = time.time()
                if now - last_debug_log >= 1.0:
                    hands_count = (
                        len(results.multi_hand_landmarks)
                        if results.multi_hand_landmarks
                        else 0
                    )
                    labels = (
                        [h.classification[0].label for h in results.multi_handedness]
                        if results.multi_handedness
                        else []
                    )
                    print(
                        " | ".join(
                            [
                                f"UDP sent={frames_sent} to {UDP_IP}:{UDP_PORT}",
                                f"hands={hands_count}",
                                f"labels={labels}",
                                f"seen_any={frames_with_any_hand}",
                                f"seen_handedness={frames_with_handedness}",
                                f"packet={packet}",
                            ]
                        )
                    )
                    last_debug_log = now
    finally:
        try:
            conn.close()
        except Exception:
            pass

tcp_sock.close()
udp_sock.close()
