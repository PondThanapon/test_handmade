FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (kept minimal); mediapipe/opencv wheels may require these.
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libstdc++6 \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./

EXPOSE 5055

CMD ["python", "main.py"]
