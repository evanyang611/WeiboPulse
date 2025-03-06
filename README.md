# WeiboScraper

微博RSS订阅和内容展示系统

## 本地开发

1. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

2. 配置环境变量
   ```bash
   # 复制环境变量模板
   cp .env.example .env
   
   # 编辑.env文件，设置你的配置
   vim .env
   ```

3. 运行应用
   ```bash
   cd src
   python main.py
   ```

## Docker 部署

### 在群晖NAS上部署

1. 安装 Docker 和 Docker Compose
   - 在群晖套件中心安装 Docker
   - 确保 Docker 已经启动

2. 准备部署
   - 将项目文件上传到群晖
   - 进入项目目录
   - 创建必要的目录结构：
     ```bash
     # 在你选择的存储位置创建目录
     mkdir -p /volume1/docker/weibo_scraper/{db,media,logs}
     mkdir -p /volume1/docker/weibo_scraper/media/{images/original,images/thumbnail,videos}
     
     # 设置目录权限（根据需要调整用户ID）
     chown -R 1000:1000 /volume1/docker/weibo_scraper
     ```

3. 配置环境变量
   编辑 docker-compose.yml 文件，设置以下环境变量：
   - `RSS_BASE_URL`: RSS源服务器地址，例如：`http://your-rss-server:port/rss/user/`
   
   或者直接使用 docker 命令运行：
   ```bash
   docker run -d \
     --name weibo_scraper \
     -p 8000:8000 \
     -v /volume1/docker/weibo_scraper/db:/app/data/db \
     -v /volume1/docker/weibo_scraper/media:/app/data/media \
     -v /volume1/docker/weibo_scraper/logs:/app/logs \
     -e TZ=Asia/Shanghai \
     -e WEB_HOST=0.0.0.0 \
     -e WEB_PORT=8000 \
     -e RSS_BASE_URL=http://your-rss-server:port/rss/user/ \
     weibo_scraper:latest
   ```

4. 构建和启动
   ```bash
   # 构建镜像并启动容器
   docker-compose up -d

   # 查看日志
   docker-compose logs -f
   ```

5. 访问
   - 打开浏览器访问 `http://群晖IP:8000`
   - 默认端口为8000，可以在 docker-compose.yml 中修改

### 数据目录说明

- `/volume1/docker/weibo_scraper/db`: 数据库文件
- `/volume1/docker/weibo_scraper/media`: 媒体文件（图片、视频）
  - `/media/images/original`: 原始图片
  - `/media/images/thumbnail`: 缩略图
  - `/media/videos`: 视频文件
- `/volume1/docker/weibo_scraper/logs`: 日志文件

### 环境变量说明

| 变量名 | 说明 | 示例 |
|--------|------|------|
| RSS_BASE_URL | RSS源服务器地址 | http://your-rss-server:port/rss/user/ |
| WEB_HOST | Web服务监听地址 | 0.0.0.0 |
| WEB_PORT | Web服务端口 | 8000 |
| TZ | 时区设置 | Asia/Shanghai |

### 注意事项

1. 首次启动时会自动创建数据库
2. 图片和视频会保存在媒体目录中
3. 日志文件按日期自动分割
4. 所有数据都保存在挂载目录中，重启容器不会丢失
5. 如果遇到权限问题，可以在 docker-compose.yml 中调整 user 配置，确保与实际用户权限匹配
6. 必须设置正确的 RSS_BASE_URL 才能正常获取微博内容

### 更新

```bash
# 停止并删除旧容器
docker-compose down

# 重新构建并启动
docker-compose up -d --build
``` 