test
# AI ตรวจสอบการเล่นเงาสำหรับ Unity
## โดยใช้โมเดล Mediapipe, YOLO V11

### วิธีใช้
* ไฟล์ **main.py** สำหรับตรวจจับท่าทาง
### วิธีติดตั้ง
```
> pip install virtualenv
> python -m venv env
> env\Scripts\activate
> pip install opencv-python ultralytics mediapipe numpy
```

## Run ด้วย Docker (แนะนำ)

โปรเจคนี้รอรับภาพจาก Unity ผ่าน TCP และส่งค่ากลับไป Unity ผ่าน UDP

### 1) สร้างและรันด้วย Docker Compose
```bash
docker compose up --build
```

### กรณี Unity รันคนละเครื่อง (ต้องระบุ IP ตอนสั่งรัน)
```bash
UNITY_IP=192.168.1.50 docker compose up --build
```

ถ้าต้องการเปลี่ยนพอร์ต UDP (ค่า default 5052):
```bash
UNITY_IP=192.168.1.50 UNITY_UDP_PORT=5052 docker compose up --build
```

### 2) ตั้งค่า Unity ให้ชี้มาที่ Docker
- Unity ส่งภาพ (TCP) ไปที่ `127.0.0.1:5055` (port นี้ถูก publish เข้า container)
- Unity รับค่าตำแหน่งมือ (UDP) ที่ `0.0.0.0:5052` หรือ `127.0.0.1:5052` บนเครื่อง host

### ข้ามอินเทอร์เน็ต (แนะนำใช้ TCP response แทน UDP)
UDP มักยิงกลับเข้าเครื่อง Unity ไม่ได้เพราะ NAT/Firewall. ทางเลือกที่เสถียรกว่า:
- ให้ Unity ส่งภาพเข้า server ผ่าน TCP ตามเดิม
- ให้ Python ส่งผลลัพธ์กลับทาง TCP เดิม (ไม่ต้องเปิดพอร์ต UDP ฝั่ง Unity)

ตั้งค่า Python ให้ส่งกลับทาง TCP:
```bash
SEND_MODE=tcp docker compose up --build
```

ตัวอย่างสคริปต์ Unity สำหรับทดสอบแบบ TCP (ส่งภาพ + รับผลลัพธ์):
- ดูไฟล์ [HandTcpCameraStreamer.cs](HandTcpCameraStreamer.cs)

### ตัวแปร Environment ที่ปรับได้
- `IMG_BIND_HOST` (default: `0.0.0.0`)
- `IMG_BIND_PORT` (default: `5055`)
- `UNITY_HOST` (default: `host.docker.internal`)
- `UNITY_PORT` (default: `5052`)
- `SEND_MODE` (default: `udp`) ค่าเป็น `udp` | `tcp` | `both`
