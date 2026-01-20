import cv2
import mediapipe as mp
import numpy as np
import socket
import struct
import os

# -----------------------------
# MediaPipe Hands
# -----------------------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

# -----------------------------
# Socket
# -----------------------------
# รับภาพจาก Unity (TCP)
sockImg = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

IMG_BIND_HOST = os.getenv("IMG_BIND_HOST", "0.0.0.0")
IMG_BIND_PORT = int(os.getenv("IMG_BIND_PORT", "5055"))

sockImg.bind((IMG_BIND_HOST, IMG_BIND_PORT))
sockImg.listen(1)

print("Waiting for Unity...")
client_socket, addr = sockImg.accept()
print("Connected:", addr)

# ส่งข้อมูลตำแหน่งมือกลับไป Unity (UDP)
sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
UNITY_HOST = os.getenv("UNITY_HOST", "host.docker.internal")
UNITY_PORT = int(os.getenv("UNITY_PORT", "5052"))
unity_target = (UNITY_HOST, UNITY_PORT)

print(f"Listening TCP on {IMG_BIND_HOST}:{IMG_BIND_PORT}")
print(f"Sending UDP to {UNITY_HOST}:{UNITY_PORT}")

# -----------------------------
# Loop
# -----------------------------
while True:

    # รับความยาวของข้อมูลภาพ
    length_data = client_socket.recv(4)
    if not length_data:
        break

    if len(length_data) < 4:
        # Incomplete header; connection likely closed.
        break

    length = struct.unpack("I", length_data)[0]

    # รับข้อมูลภาพจริง
    image_data = b""
    while len(image_data) < length:
        chunk = client_socket.recv(length - len(image_data))
        if not chunk:
            image_data = b""
            break
        image_data += chunk

    if not image_data:
        break

    np_arr = np.frombuffer(image_data, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None:
        continue

    h, w, _ = frame.shape

    # ตรวจจับมือ
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    SendValue = ""

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:

            SendHandData = []

            # เก็บตำแหน่ง 21 landmark
            for lm in hand_landmarks.landmark:
                X = int(lm.x * w)
                Y = int(h - (lm.y * h))  # กลับแกน Y แบบเดิม
                Z = int(lm.z * h)

                SendHandData.extend([X, Y, Z])

            # แปลงเป็น string แบบต้นฉบับ
            SendValue += f"{str(SendHandData)}_"

        # ตัด '_' ตัวสุดท้ายออกก่อนส่ง
        SendValue = SendValue[:-1]

        sock_send.sendto(SendValue.encode(), unity_target)

# -----------------------------
# Clean up
# -----------------------------
client_socket.close()
sockImg.close()
sock_send.close()
