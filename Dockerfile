FROM python:3.9-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ src/

# 创建必要的目录
RUN mkdir -p /app/data/db \
    /app/data/media/images \
    /app/data/media/videos \
    /app/logs

# 设置环境变量
ENV PYTHONPATH=/app
ENV DATA_DIR=/app/data
ENV LOG_DIR=/app/logs

# 暴露API端口
EXPOSE 8000

# 运行应用
CMD ["python", "src/main.py"]
