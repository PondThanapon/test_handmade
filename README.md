# AI ตรวจสอบการเล่นเงาสำหรับ Unity
## โดยใช้โมเดล Mediapipe, YOLO V11

### วิธีใช้
* ไฟล์ **main.py** สำหรับตรวจจับท่าทาง
* ไฟล์ **calibrate.py** สำหรับจูนสีผิว
* ไฟล์ **savevalue.py** สำหรับการเก็บข้อมูลสำหรับการเทรน
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

### 2) ตั้งค่า Unity ให้ชี้มาที่ Docker
- Unity ส่งภาพ (TCP) ไปที่ `127.0.0.1:5055` (port นี้ถูก publish เข้า container)
- Unity รับค่าตำแหน่งมือ (UDP) ที่ `0.0.0.0:5052` หรือ `127.0.0.1:5052` บนเครื่อง host

### ตัวแปร Environment ที่ปรับได้
- `IMG_BIND_HOST` (default: `0.0.0.0`)
- `IMG_BIND_PORT` (default: `5055`)
- `UNITY_HOST` (default: `host.docker.internal`)
- `UNITY_PORT` (default: `5052`)
