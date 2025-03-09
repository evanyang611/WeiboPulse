# 使用官方Python基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置Python环境
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制源代码
COPY src/ src/

# 设置工作目录为src
WORKDIR /app/src

# 启动命令
CMD ["python", "web.py"]
