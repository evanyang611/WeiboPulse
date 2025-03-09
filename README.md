# WeiboPulse

微博RSS订阅和内容展示系统，支持定时抓取微博内容、话题总结和内容展示。

## 功能特点

- 🔄 **RSS订阅**：通过RSS源订阅微博账号内容
- 📊 **定时抓取**：自动定时抓取和更新微博内容
- 🖼️ **媒体下载**：自动下载和存储微博中的图片和视频
- 🤖 **AI总结**：使用阿里云千问大模型对微博内容进行话题总结
- 🌐 **Web界面**：提供美观的Web界面展示微博内容和话题总结
- 👥 **账号分组**：支持微博账号分组和管理
- 🔍 **内容检索**：支持按时间、账号、关键词等检索微博内容

## 技术栈

- **后端**：Python + FastAPI
- **数据库**：SQLite
- **定时任务**：APScheduler
- **AI模型**：阿里云千问大模型
- **部署**：Docker + Docker Compose

## 快速开始

### 前提条件

- Docker 和 Docker Compose 已安装
- 阿里云千问API密钥（可选，用于AI总结功能）

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/yourusername/WeiboPulse.git
cd WeiboPulse
```

2. **修改配置**

编辑 `docker-compose.yml` 文件，根据需要修改环境变量：

```yaml
environment:
  - TZ=Asia/Shanghai                                    # 时区设置
  - WEB_HOST=0.0.0.0                                    # Web服务监听地址
  - WEB_PORT=8000                                       # Web服务监听端口
  - RSS_BASE_URL=http://your-rss-server:port/rss/user/  # RSS源地址
  - ALIYUN_API_KEY=your-api-key                         # 阿里云千问API密钥
  - TEXT_MODEL=qwen-max-latest                          # 纯文本模型
  - MULTIMODAL_MODEL=qwen-omni-turbo-latest             # 多模态模型
  - DATA_DIR=/app/data                                  # 数据目录
```

3. **启动服务**

```bash
docker-compose up -d
```

4. **访问Web界面**

服务启动后，通过浏览器访问：

```
http://your-host-ip:8101
```

## 使用说明

### 添加微博账号

1. 访问Web界面
2. 点击"设置"菜单
3. 在"账号管理"部分，输入微博账号ID并点击"添加"

### 设置定时任务

1. 访问Web界面
2. 点击"设置"菜单
3. 在"定时任务"部分，设置抓取频率和分组

### 查看话题总结

1. 访问Web界面
2. 点击"消息"菜单
3. 查看由AI生成的话题总结
