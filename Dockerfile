FROM python:3.13-slim

# Cài đặt các công cụ biên dịch hệ thống cần thiết cho C++ và Git
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    curl \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Thiết lập biến môi trường chạy Python mượt hơn
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Sao chép và cài đặt danh sách thư viện từ requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# TỰ ĐỘNG TẢI FILE TPK VÀO ĐÚNG ĐƯỜNG DẪN THƯ MỤC CỦA PYTHON 3.13
RUN mkdir -p /usr/local/lib/python3.13/site-packages/UnityPy && \
    curl -L -o /usr/local/lib/python3.13/site-packages/UnityPy/UnityPy.tpk https://github.com/K0lb3/UnityPy/raw/master/UnityPy/UnityPy.tpk

# Sao chép toàn bộ mã nguồn bot vào container
COPY . .

# Lệnh khởi chạy bot chính thức
CMD ["python", "aov.py"]
