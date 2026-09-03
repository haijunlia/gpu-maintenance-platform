# GPU QC 分析系统 (Vue3 SPA版本)

> 当前发布基线：[`VERSION`](VERSION)（1.2.0）。变更记录见 [`CHANGELOG.md`](CHANGELOG.md)，发布步骤见 [`RELEASING.md`](RELEASING.md)。

## 项目概述

这是一个基于Vue3 SPA架构的GPU QC（质量控制）数据查询和分析系统。系统采用前后端分离的架构，提供现代化的用户界面和强大的数据分析功能。系统支持智能SN范围合并显示，能够将连续的SN自动合并为范围格式，提高数据可读性。

## 技术架构

### 前端 (Frontend)
- **框架**: Vue 3 + Composition API
- **构建工具**: Vite
- **UI框架**: Element Plus
- **图表库**: Chart.js
- **HTTP客户端**: Axios
- **路由**: Vue Router 4

### 后端 (Backend)
- **框架**: FastAPI (Python 3.12+)
- **数据库**: PostgreSQL
- **ORM**: 原生SQL查询
- **API文档**: 自动生成的OpenAPI文档

### 部署
- **开发环境**: 前后端分离开发
- **生产环境**: 单容器部署 (Docker)
- **数据库**: PostgreSQL容器

## 功能特性

- 🔍 **多条件查询**: 支持按日期、状态、错误代码、SN范围等条件筛选
- 📊 **数据可视化**: 错误代码分布图、服务器分布图
- 📈 **统计分析**: 通过率统计、GPU数量统计等
- 🏷️ **智能SN合并**: 自动将连续SN合并为范围显示（如：TL538R0320001-TL538R0320005）
- ✏️ **数据编辑**: 支持在线编辑记录数据，实时更新统计信息
- 📄 **数据导出**: CSV格式导出查询结果
- 📱 **响应式设计**: 支持桌面和移动设备
- 🔄 **实时更新**: 支持数据实时查询和更新

## 快速开始

### 环境要求

- Node.js 18+
- Python 3.12+
- PostgreSQL 12+
- npm 或 yarn

### 开发环境

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd gpu-qc-analysis
   ```

2. **安装后端依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置数据库**
   - 创建PostgreSQL数据库
   - 准备数据库结构：
     - 如果是全新空库，可以使用 `schema.sql` 做最小初始化
     - 如果你有生产环境导出的备份，优先直接恢复生产备份
   - 创建 `.env` 文件并配置数据库连接信息：
     ```bash
     DATABASE_URL=postgresql://postgres:密码@localhost:5432/tsm
     DB_MIN_CONNECTIONS=1
     DB_MAX_CONNECTIONS=20
     ```

4. **启动开发服务器**
    ```bash
    python -m app.main
    ```
    
    这将自动检测运行模式：
    - **开发模式**（无frontend/dist目录）：仅启动后端开发服务器
      - 后端API服务器: http://localhost:8000
      - 前端开发服务器: 需要单独启动（cd frontend && npm run dev）
    - **生产模式**（有frontend/dist目录）：启动生产服务器
      - 完整应用: http://localhost:80

### 生产环境

1. **构建前端**
   ```bash
   cd frontend
   npm install
   npm run build
   ```

   **说明**: 仅执行 `git clone` 拉取源码时，项目默认只有前端源码，没有 `frontend/dist` 构建产物；此时直接运行 `python -m app.main` 会进入开发模式。必须先执行上面的前端构建命令，生成 `frontend/dist` 后，项目才会自动进入生产模式。

2. **启动生产服务器**
   ```bash
   python -m app.main
   ```
   或者直接运行：
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 80
   ```

   **注意**: 如果 `frontend/dist` 目录存在，系统会自动以生产模式启动（端口80）。

3. **访问应用**
   - 打开浏览器访问: http://localhost:80

### 本地数据库备份与恢复

如果你在本机使用 PostgreSQL，推荐直接用 `pg_dump`、`psql` 和 `pg_restore` 管理备份。  
对于这个项目，**生产环境导出的备份通常比手工维护的 `schema.sql` 更权威**，因为备份一般同时包含真实表结构、索引和数据。

#### 连接参数准备

先根据你的本地数据库环境设置连接参数：

```bash
export PGHOST=localhost
export PGPORT=5432
export PGUSER=postgres
export PGPASSWORD='你的密码'
```

如果你的数据库名是 `tsm`，下面命令里的 `<db_name>` 就替换成 `tsm`。

#### 1. 导出 SQL 备份

```bash
pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" \
  -d <db_name> \
  -f tsm_backup.sql
```

这条命令会导出数据库结构和数据，生成一个可直接导入的 `.sql` 文件。

#### 2. 导入 SQL 备份

先创建一个空数据库，再执行恢复：

```bash
createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" <new_db_name>
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" \
  -d <new_db_name> \
  -f tsm_backup.sql
```

如果目标库已经存在，且你就是想完全覆盖恢复，最稳妥的方式是先删库再建库：

```bash
dropdb --if-exists -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" <target_db_name>
createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" <target_db_name>
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" \
  -d <target_db_name> \
  -f tsm_backup.sql
```

#### 3. 只初始化空库结构

如果你没有生产备份，只想先拉起一个最小可用的空库，可以使用项目内的 `schema.sql`：

```bash
createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" <db_name>
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" \
  -d <db_name> \
  -f schema.sql
```

这条路径只适合“初始化空库结构”，不包含生产数据。

#### 4. 恢复后怎么接入项目

恢复完成后，把 `.env` 里的 `DATABASE_URL` 指向你恢复后的数据库，例如：

```bash
DATABASE_URL=postgresql://postgres:密码@localhost:5432/tsm
```

然后启动后端：

```bash
python -m app.main
```

### Docker部署

Docker 现在更适合作为一个可选的打包/部署方式，不再作为数据库初始化或恢复的主路径。

1. **使用Docker Compose启动**
   ```bash
   docker-compose up -d
   ```

2. **访问应用**
   - 应用: http://localhost:80
   - 数据库: localhost:5432

说明：
- 如果你只是本地开发或本地恢复数据库，优先参考上面的“本地数据库备份与恢复”
- Docker 相关数据库恢复脚本 [`scripts/restore_db.sh`](scripts/restore_db.sh) 仅用于容器内 PostgreSQL 的恢复辅助，不是默认工作流

## 项目结构

```
gpu-qc-analysis/
├── app/                    # 后端应用
│   ├── api/               # API路由
│   │   └── routes.py      # 主要API端点（查询、编辑、导出等）
│   ├── core/              # 核心配置
│   │   └── db.py          # 数据库连接配置
│   ├── crud/              # 数据库操作
│   │   └── query_db.py    # 查询和更新数据库操作
│   ├── schemas/           # 数据模型
│   │   └── models.py      # Pydantic数据模型定义
│   ├── service/           # 业务逻辑
│   │   └── data_service.py # 数据处理和SN合并逻辑
│   └── main.py            # FastAPI应用入口
├── frontend/              # 前端应用
│   ├── src/
│   │   ├── components/    # Vue组件
│   │   │   ├── StatsSummary.vue    # 统计摘要组件（含SN范围显示）
│   │   │   ├── ResultsTable.vue    # 结果表格组件（含编辑功能）
│   │   │   ├── EditDialog.vue      # 编辑对话框组件
│   │   │   └── ...                 # 其他组件
│   │   ├── views/         # 页面视图
│   │   │   └── Home.vue            # 主页面
│   │   ├── composables/   # 组合式API
│   │   │   ├── useGpuData.js       # 数据管理
│   │   │   └── useCharts.js        # 图表管理
│   │   ├── services/      # API服务
│   │   │   └── api.js              # API调用封装
│   │   └── assets/        # 静态资源
│   ├── public/            # 公共资源
│   └── dist/              # 构建输出
├── collection.py          # 数据采集脚本
├── add_log.py             # 日志添加脚本
├── schema.sql             # 数据库初始化脚本
├── scripts/
│   └── restore_db.sh      # Docker环境数据库恢复辅助脚本
├── Dockerfile             # Docker配置
├── docker-compose.yml     # Docker Compose配置
├── requirements.txt       # Python依赖
└── README.md              # 项目文档
```

## API文档

启动后端服务器后，可以访问以下地址查看API文档：

- Swagger UI: http://localhost:8000/docs (开发模式) 或 http://localhost:80/docs (生产模式)
- ReDoc: http://localhost:8000/redoc (开发模式) 或 http://localhost:80/redoc (生产模式)
- 健康检查: http://localhost:8000/api/health (开发模式) 或 http://localhost:80/api/health (生产模式)
- 数据库健康检查: http://localhost:8000/api/health/db (开发模式) 或 http://localhost:80/api/health/db (生产模式)

### 主要API端点

- `GET /api/filters` - 获取筛选器选项
- `POST /api/query` - 查询记录（支持分页和统计）
- `PUT /api/record/{record_id}` - 更新指定记录
- `POST /api/export/csv` - 导出CSV文件
- `GET /api/health` - 应用健康检查
- `GET /api/health/db` - 数据库健康检查
- `GET /api/health/pool` - 连接池状态检查

## 开发指南

### 前端开发

1. **添加新组件**
   ```bash
   # 在 frontend/src/components/ 目录下创建新组件
   ```

2. **添加新页面**
   ```bash
   # 在 frontend/src/views/ 目录下创建新页面
   # 在 frontend/src/main.js 中添加路由配置
   ```

3. **API调用**
   ```javascript
   // 使用 composables/useGpuData.js 中的方法
   import { gpuApi } from '@/services/api'
   ```

### 后端开发

1. **添加新API端点**
   ```python
   # 在 app/api/routes.py 中添加新路由
   ```

2. **数据库操作**
   ```python
   # 在 app/crud/ 目录下添加新的数据库操作
   ```

3. **数据模型**
   ```python
   # 在 app/schemas/models.py 中定义新的数据模型
   ```

## 数据采集

系统包含一个独立的数据采集脚本 `collection.py`，用于：

- 解析GPU测试日志文件
- 将数据同步到PostgreSQL数据库
- 支持增量更新和全量覆盖

使用方法：
```bash
python collection.py
```

## SN合并显示逻辑

系统实现了智能SN范围合并功能，能够自动识别和合并连续的SN，提高数据可读性。

### SN格式说明

系统支持的SN格式：`TL538R032XXXX`
- `TL538`: 固定前缀
- `538`: 3位周数（会变化，如539、540等）
- `R`: 供应商缩写
- `032`: 3位产品类型
- `XXXX`: 4位序列号（0001-9999）

### 合并规则

1. **相同周数和产品类型**: 只有相同周数和产品类型的SN才会被合并
2. **连续序列号**: 序列号必须连续（如0001, 0002, 0003）
3. **最小合并数量**: 2个或以上连续SN才会显示为范围
4. **范围格式**: `起始SN-结束SN`（如：TL538R0320001-TL538R0320005）

### 合并示例

**输入SN列表**:
```
TL538R0320001, TL538R0320002, TL538R0320003, TL538R0320005, TL538R0320006
TL539R0320001, TL539R0320002, TL539R0320003
TL538R0330001, TL538R0330002
```

**合并结果**:
```
TL538R0320001-TL538R0320003, TL538R0320005-TL538R0320006
TL539R0320001-TL539R0320003
TL538R0330001-TL538R0330002
```

### 技术实现

- **后端**: 使用正则表达式解析SN格式，按前缀分组，检测连续序列号
- **前端**: 在统计摘要中以标签形式展示合并后的SN范围
- **样式**: 使用蓝色渐变主题，悬停动画效果，提升用户体验

## 配置说明

### 环境变量

项目已包含 `.env` 文件，请根据您的环境修改配置：

```bash
# 数据库配置
DATABASE_URL=postgresql://用户名:密码@地址:5432/tsm

# 连接池配置
DB_MIN_CONNECTIONS=1
DB_MAX_CONNECTIONS=20

# 应用配置
DEBUG=True
LOG_LEVEL=INFO

# 前端配置
VITE_API_BASE_URL=http://localhost:8000
```

**重要**: 请根据您的实际数据库环境修改 `DATABASE_URL` 配置。

### 连接池配置

系统使用PostgreSQL连接池来优化数据库连接管理：

- **DB_MIN_CONNECTIONS**: 最小连接数（默认：1）
- **DB_MAX_CONNECTIONS**: 最大连接数（默认：20）

连接池状态监控：
- 健康检查: `GET /api/health/pool`
- 数据库检查: `GET /api/health/db`

### 数据库索引优化

系统提供数据库索引优化方案，显著提升查询性能：

#### 优化内容
- **基础索引**: 时间戳、状态、错误代码、SN、服务器IP等
- **复合索引**: 状态+时间戳、SN+状态、错误代码+时间戳等
- **部分索引**: 只对失败记录、通过记录建索引，节省空间
- **覆盖索引**: 包含查询所需的所有列，减少回表查询

#### 应用优化
```bash
# 运行索引优化脚本
python apply_index_optimization.py
```

#### 性能提升
- 查询性能提升: 60-90%
- 时间范围查询: 提升 70-85%
- 状态筛选查询: 提升 50-70%
- SN范围查询: 提升 80-95%

#### 索引说明
- 时间戳索引（降序）: 优化按时间排序的查询
- 状态索引: 优化按状态筛选的查询
- 错误代码索引: 优化错误分析查询
- 复合索引: 优化多条件组合查询
- 部分索引: 针对特定状态优化，节省存储空间

### 前端配置

在 `frontend/vite.config.js` 中配置：

```javascript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

## 快速诊断

### 数据库连接问题

如果遇到503错误（Service Unavailable），通常是数据库连接问题：

1. **检查数据库服务**：
   - 确保PostgreSQL服务正在运行
   - 检查端口5432是否开放
   - 验证数据库用户权限

2. **使用Docker启动数据库**：
   ```bash
   docker-compose up -d db
   ```

3. **检查网络连接**：
   - 如果使用远程数据库，检查网络连通性
   - 检查防火墙设置

## 故障排除

### 常见问题

1. **前端无法连接后端API**
   - 检查后端服务器是否启动
   - 检查CORS配置
   - 检查代理配置

2. **数据库连接失败**
    - 检查数据库服务是否运行
    - 检查 `.env` 文件中的 `DATABASE_URL` 配置
    - 检查数据库权限和网络连接

3. **构建失败**
   - 检查Node.js版本
   - 清除node_modules重新安装
   - 检查网络连接

### 日志查看

- 应用日志: `logs/` 目录
- 开发日志: 浏览器控制台
- 构建日志: 终端输出



## 贡献

贡献流程、测试要求和安全规范请见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 版本与发布

当前正式版本为 [`v1.2.0`](https://github.com/GD-TRNGT/gpu-qc-analysis/releases/tag/v1.2.0)。版本号以根目录 [`VERSION`](VERSION)、前端 `package.json` 和 Git 标签为准。

- [`v1.0.0`](https://github.com/GD-TRNGT/gpu-qc-analysis/releases/tag/v1.0.0)：原 `main` 分支的稳定基线。
- [`v1.2.0`](https://github.com/GD-TRNGT/gpu-qc-analysis/releases/tag/v1.2.0)：增加 MODS 测试、综合判定、包装前验证、GPU 型号筛选及发布流程。

详细变更请查看 [CHANGELOG.md](CHANGELOG.md)，发布步骤请查看 [RELEASING.md](RELEASING.md)。README 不再维护独立的内嵌版本历史；正式版本以 Git 标签和 GitHub Release 为准。
