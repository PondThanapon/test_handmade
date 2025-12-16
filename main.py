import cv2
import mediapipe as mp
import numpy as np
import socket
import struct

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
sockImg.bind(("127.0.0.1", 5055))
sockImg.listen(1)

print("Waiting for Unity...")
client_socket, addr = sockImg.accept()
print("Connected:", addr)

# ส่งข้อมูลตำแหน่งมือกลับไป Unity (UDP)
sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
unity_target = ("127.0.0.1", 5052)

# -----------------------------
# Loop
# -----------------------------
while True:

    # รับความยาวของข้อมูลภาพ
    length_data = client_socket.recv(4)
    if not length_data:
        break

    length = struct.unpack("I", length_data)[0]

    # รับข้อมูลภาพจริง
    image_data = b""
    while len(image_data) < length:
        image_data += client_socket.recv(length - len(image_data))

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
