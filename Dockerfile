FROM python:3.12-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製代碼
COPY . .

# 運行
CMD ["python", "app.py"]
