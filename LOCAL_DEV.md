# 本地开发指南

本文档说明如何在 macOS 上直接运行 AssetRipper API Server（不使用 Docker）。

## 前置要求

- Python 3.11+
- macOS 操作系统
- AssetRipper macOS 版本二进制文件

## 快速开始

### 1. 下载 AssetRipper macOS 版本

访问 [AssetRipper Releases](https://github.com/AssetRipper/AssetRipper/releases) 下载最新的 macOS 版本。

解压后，将 `AssetRipper.GUI.Free` 文件放置到以下位置之一：

```bash
# 推荐位置（本地开发专用）
local/AssetRipper.GUI.Free

# 或使用项目自带的位置
bin/AssetRipper.GUI.Free
```

**重要**: 请确保下载的是 **macOS** 版本，而不是 Linux 或 Windows 版本。

### 2. 启动服务

#### 方式 1: 前台启动（推荐用于开发调试）

```bash
./start.sh
```

前台启动会占用当前终端，并显示实时日志。按 `Ctrl+C` 停止服务。

**特点：**
- ✅ 实时查看日志输出
- ✅ 代码修改自动重载
- ✅ 适合开发调试
- ⚠️ 占用终端窗口

#### 方式 2: 后台启动（推荐用于长时间运行）

```bash
./start.sh -d
# 或
./start.sh --daemon
```

后台启动会在后台运行服务，不占用终端。

**特点：**
- ✅ 不占用终端窗口
- ✅ 适合长时间运行
- ✅ 服务在后台持续运行
- 💡 需要使用 `./stop.sh` 停止

### 3. 访问服务

启动成功后，可以访问：

- **API 根路径**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/v1/health

### 4. 管理服务

#### 查看日志

```bash
# 前台启动：直接在终端查看

# 后台启动：查看日志文件
tail -f logs/uvicorn.log      # Uvicorn 日志
tail -f logs/app.log          # 应用日志
tail -f logs/app.log.assetripper  # AssetRipper 日志
```

#### 停止服务

```bash
./stop.sh
```

这个脚本会：
- 停止 uvicorn 进程
- 停止 AssetRipper 进程
- 优雅关闭，如果失败则强制终止

#### 重启服务

```bash
./restart.sh
```

等同于执行 `./stop.sh` 然后 `./start.sh -d`

## 目录结构

本地运行时的目录结构：

```
AssetRipperServer/
├── local/                        # 本地开发专用（不会提交到 git）
│   └── AssetRipper.GUI.Free      # macOS 版本的 AssetRipper
├── data/                         # 数据目录（不会提交到 git）
│   ├── uploads/                  # 上传的文件
│   ├── exports/                  # 导出的 Assets
│   └── db/                       # SQLite 数据库
├── logs/                         # 日志目录（不会提交到 git）
│   └── app.log                   # 应用日志
├── .venv/                        # Python 虚拟环境（不会提交到 git）
└── start.sh                      # 一键启动脚本
```

## 环境变量配置

启动脚本会自动配置以下环境变量，如需修改可以编辑 `start.sh`:

```bash
API_PORT=8000                     # API 服务端口
ASSETRIPPER_PORT=8765             # AssetRipper 内部端口
FILE_RETENTION_DAYS=30            # 文件保留天数
LOG_LEVEL=INFO                    # 日志级别
```

## 手动启动（高级）

如果需要手动控制启动过程：

```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 设置环境变量
export ASSETRIPPER_BINARY_PATH="$(pwd)/local/AssetRipper.GUI.Free"
export DATABASE_URL="sqlite+aiosqlite:///$(pwd)/data/db/assetripper.db"
export UPLOAD_DIR="$(pwd)/data/uploads"
export EXPORT_DIR="$(pwd)/data/exports"

# 3. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 常见问题

### Q: 提示找不到 AssetRipper.GUI.Free？

**A**: 请确保已下载 macOS 版本的 AssetRipper 并放置到 `local/` 目录。

### Q: 启动失败，提示权限错误？

**A**: 给 AssetRipper 添加执行权限：
```bash
chmod +x local/AssetRipper.GUI.Free
```

### Q: macOS 提示无法打开未验证的开发者应用？

**A**: 在系统设置中允许运行：
1. 打开 "系统设置" -> "隐私与安全性"
2. 找到被阻止的应用，点击 "仍要打开"

或使用命令行：
```bash
xattr -d com.apple.quarantine local/AssetRipper.GUI.Free
```

### Q: 如何查看日志？

**A**: 日志文件位于 `logs/app.log`：
```bash
tail -f logs/app.log
```

### Q: 如何清理所有数据重新开始？

**A**: 删除数据目录：
```bash
rm -rf data/ logs/ .venv/
```

然后重新运行 `./start.sh`。

## 与 Docker 版本的区别

| 特性 | 本地运行 | Docker 运行 |
|------|---------|------------|
| 启动速度 | 快 | 较慢（需构建镜像） |
| 依赖管理 | 需手动安装 Python | 全自动 |
| 数据位置 | 项目目录 | Docker 卷 |
| 适用场景 | 开发调试 | 生产部署 |
| 系统要求 | macOS + Python | 任意系统 + Docker |

## 开发建议

1. **使用热重载**: 启动脚本默认启用了 `--reload` 选项，代码修改后会自动重启
2. **查看实时日志**: 使用 `tail -f logs/app.log` 查看应用日志
3. **API 测试**: 访问 http://localhost:8000/docs 使用交互式 API 文档
4. **数据清理**: 开发时可以定期清理 `data/` 目录避免占用过多空间

## 相关文档

- [主 README](README.md) - 项目总览和 Docker 部署
- [API 文档](http://localhost:8000/docs) - 启动服务后访问
