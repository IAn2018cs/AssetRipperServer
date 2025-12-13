# AssetRipper API Server

AssetRipper API Server 是一个基于 FastAPI 的 RESTful API 服务，用于从 APK/XAPK/IPA 文件中提取 Unity Assets 资源。它包装了 [AssetRipper](https://github.com/AssetRipper/AssetRipper) 工具，提供了易于使用的 HTTP API。

## 功能特性

- 上传 APK/XAPK/IPA 文件并自动提取 Unity Assets
- 基于队列的任务处理系统（顺序处理）
- 任务状态查询
- 导出资源下载（ZIP 格式）
- 自动文件清理（30 天）
- 健康检查端点
- Docker 部署支持
- 持久化数据存储（SQLite）

## 技术栈

- **Web 框架**: FastAPI
- **异步运行时**: asyncio
- **数据库**: SQLite + SQLAlchemy
- **任务队列**: asyncio.Queue
- **文件清理**: APScheduler
- **容器化**: Docker + Docker Compose

## 项目结构

```
AssetRipperServer/
├── app/                          # 应用代码
│   ├── api/v1/endpoints/         # API 端点
│   ├── core/                     # 核心组件
│   │   ├── assetripper.py        # AssetRipper 进程管理器
│   │   ├── task_queue.py         # 任务队列处理器
│   │   └── file_cleanup.py       # 文件清理调度器
│   ├── config.py                 # 配置管理
│   ├── database.py               # 数据库设置
│   ├── models.py                 # 数据库模型
│   ├── schemas.py                # Pydantic 模型
│   └── main.py                   # 应用入口
├── bin/                          # AssetRipper 二进制文件
│   ├── AssetRipper.GUI.Free
│   └── libcapstone.so
├── docker/                       # Docker 相关文件
│   └── entrypoint.sh
├── Dockerfile                    # Docker 镜像定义
├── docker-compose.yml            # Docker Compose 配置
├── requirements.txt              # Python 依赖
└── .env.example                  # 环境变量模板
```

## 快速开始

### Docker 部署（推荐用于生产环境）

#### 前置要求

- Docker 和 Docker Compose

#### 部署步骤

1. **克隆项目**

```bash
cd AssetRipperServer
```

2. **配置环境变量**

```bash
cp .env.example .env
# 编辑 .env 文件，设置所需的环境变量
nano .env
```

3. **启动服务**

```bash
docker-compose up -d
```

4. **查看日志**

```bash
docker-compose logs -f
```

5. **访问 API**

- API 根路径: `http://localhost:8000`
- API 文档: `http://localhost:8000/docs`
- 健康检查: `http://localhost:8000/api/v1/health`

### 本地开发（推荐用于开发调试）

如需在 macOS 上直接运行服务（不使用 Docker），请参考 **[本地开发指南](LOCAL_DEV.md)**。

**一键启动：**
```bash
./start.sh
```

详细说明请查看 [LOCAL_DEV.md](LOCAL_DEV.md)。

## API 使用示例

### 1. 上传文件

```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/game.apk"
```

响应示例:

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "message": "File uploaded successfully. Task queued for processing.",
  "created_at": "2025-12-13T10:30:00Z"
}
```

### 2. 查询任务状态

```bash
curl "http://localhost:8000/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000"
```

响应示例:

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "original_filename": "game.apk",
  "created_at": "2025-12-13T10:30:00Z",
  "started_at": "2025-12-13T10:30:15Z",
  "completed_at": "2025-12-13T10:35:42Z",
  "file_size_bytes": 104857600,
  "export_path": "/api/v1/download/550e8400-e29b-41d4-a716-446655440000",
  "export_size_bytes": 52428800,
  "error_message": null
}
```

任务状态说明:
- `PENDING`: 等待处理
- `PROCESSING`: 正在处理
- `COMPLETED`: 已完成
- `FAILED`: 处理失败

### 3. 下载导出的 Assets

```bash
curl -O -J "http://localhost:8000/api/v1/download/550e8400-e29b-41d4-a716-446655440000"
```

### 4. 删除任务

```bash
curl -X DELETE "http://localhost:8000/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000"
```

### 5. 健康检查

```bash
curl "http://localhost:8000/api/v1/health"
```

响应示例:

```json
{
  "status": "healthy",
  "assetripper_status": "running",
  "queue_size": 3,
  "current_task": "550e8400-e29b-41d4-a716-446655440000",
  "uptime_seconds": 86400
}
```

## 环境变量配置

在 `.env` 文件中可以配置以下环境变量：

```env
# API 端口（默认: 8000）
API_PORT=8000

# 日志级别（DEBUG, INFO, WARNING, ERROR）
LOG_LEVEL=INFO

# 文件保留天数（默认: 30）
FILE_RETENTION_DAYS=30

# AssetRipper 配置
# 使用外部 AssetRipper 实例（如果设置，将不会启动 AssetRipper 进程）
# ASSETRIPPER_HOST=http://localhost:8765
```

**使用外部 AssetRipper 实例：**

如果遇到 AssetRipper 启动问题，可以手动启动 AssetRipper 并配置应用使用外部实例：

```bash
# 1. 手动启动 AssetRipper（本地开发）
cd local
./AssetRipper.GUI.Free --port 8765 --launch-browser=false

# 2. 在 .env 文件中配置
ASSETRIPPER_HOST=http://localhost:8765

# 3. 启动 API 服务
./start.sh
```

设置 `ASSETRIPPER_HOST` 后，应用将：
- 跳过启动 AssetRipper 进程
- 连接到指定的外部实例
- 不尝试重启或管理外部进程
- 仍会通过 HTTP 进行健康检查


## Docker Compose 配置

`docker-compose.yml` 文件包含以下关键配置：

### 端口映射

- 主机端口 -> 容器端口: `${API_PORT:-8000}:8000`
- 可通过 `.env` 文件中的 `API_PORT` 变量修改

### 数据卷挂载

以下目录会持久化到 Docker 卷中，防止容器重启时数据丢失：

- `assetripper-uploads`: 上传的文件
- `assetripper-exports`: 导出的 Assets
- `assetripper-db`: SQLite 数据库
- `assetripper-logs`: 应用日志

### 资源限制

默认资源配置：
- CPU: 2-4 核
- 内存: 2-8 GB

可根据实际需求在 `docker-compose.yml` 中调整。

## 管理命令

### 启动服务

```bash
docker-compose up -d
```

### 停止服务

```bash
docker-compose down
```

### 查看日志

```bash
# 查看所有日志
docker-compose logs -f

# 只查看最近 100 行
docker-compose logs --tail=100 -f
```

### 重启服务

```bash
docker-compose restart
```

### 重新构建镜像

```bash
docker-compose build --no-cache
docker-compose up -d
```

### 查看容器状态

```bash
docker-compose ps
```

### 进入容器

```bash
docker-compose exec assetripper-api bash
```

## 备份与恢复

### 备份数据

备份所有 Docker 卷：

```bash
# 创建备份目录
mkdir -p backups/$(date +%Y%m%d)

# 备份数据库
docker run --rm \
  -v assetripperserver_assetripper-db:/source \
  -v $(pwd)/backups/$(date +%Y%m%d):/backup \
  alpine tar czf /backup/db.tar.gz -C /source .

# 备份上传文件
docker run --rm \
  -v assetripperserver_assetripper-uploads:/source \
  -v $(pwd)/backups/$(date +%Y%m%d):/backup \
  alpine tar czf /backup/uploads.tar.gz -C /source .

# 备份导出文件
docker run --rm \
  -v assetripperserver_assetripper-exports:/source \
  -v $(pwd)/backups/$(date +%Y%m%d):/backup \
  alpine tar czf /backup/exports.tar.gz -C /source .
```

### 恢复数据

```bash
# 恢复数据库
docker run --rm \
  -v assetripperserver_assetripper-db:/target \
  -v $(pwd)/backups/YYYYMMDD:/backup \
  alpine sh -c "rm -rf /target/* && tar xzf /backup/db.tar.gz -C /target"
```

## 故障排查

### 1. AssetRipper 启动失败

查看日志：

```bash
docker-compose logs assetripper-api | grep AssetRipper
```

可能原因：
- 二进制文件缺少执行权限
- 系统库缺失
- 端口被占用

**解决方法：**

使用外部 AssetRipper 实例：

```bash
# 手动启动 AssetRipper
./AssetRipper.GUI.Free --port 8765 --launch-browser=false

# 在 .env 中添加
ASSETRIPPER_HOST=http://localhost:8765

# 重启服务
docker-compose restart
```

### 2. 任务一直处于 PENDING 状态

检查任务队列是否正常运行：

```bash
curl "http://localhost:8000/api/v1/health"
```

### 3. 容器重启后任务丢失

检查数据卷是否正确挂载：

```bash
docker volume ls | grep assetripper
```

### 4. 磁盘空间不足

清理旧任务：

```bash
# 手动触发清理
# 或者调整 FILE_RETENTION_DAYS 环境变量
```

查看磁盘使用：

```bash
docker system df
```

## 性能优化

### 1. 调整资源限制

根据服务器性能调整 `docker-compose.yml` 中的资源限制：

```yaml
deploy:
  resources:
    limits:
      cpus: '8'      # 增加 CPU 核心数
      memory: 16G    # 增加内存
```

### 2. 调整文件保留期

减少文件保留天数可以节省磁盘空间：

```env
FILE_RETENTION_DAYS=7
```

### 3. 定期清理 Docker 资源

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的卷
docker volume prune

# 清理所有未使用的资源
docker system prune -a --volumes
```

## 安全建议

1. **网络隔离**: 建议在内网环境部署，避免直接暴露到公网
2. **定期备份**: 定期备份数据库和重要文件
3. **资源监控**: 监控 CPU、内存和磁盘使用情况
4. **日志审计**: 定期检查应用日志

## 开发指南

### 本地开发

1. 安装 Python 依赖：

```bash
pip install -r requirements.txt
```

2. 配置环境变量：

```bash
cp .env.example .env
# 修改 ASSETRIPPER_BINARY_PATH 指向本地 AssetRipper 二进制文件
```

3. 运行开发服务器：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 许可证

本项目基于 AssetRipper 工具构建，请遵守 AssetRipper 的许可证要求。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请通过 Issue 联系。
