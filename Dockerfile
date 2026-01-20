FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  PIP_DEFAULT_TIMEOUT=300

WORKDIR /app

# System deps (kept minimal); mediapipe/opencv wheels may require these.
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    libxcb1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxkbcommon0 \
    libgl1 \
    libglib2.0-0 \
    libstdc++6 \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir --retries 10 --timeout 300 -r requirements.txt

COPY main.py ./

EXPOSE 5055

CMD ["python", "main.py"]
