
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes
import os

# 检查是否为生产模式（存在frontend/dist目录）
IS_PRODUCTION = os.path.exists("frontend/dist")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if IS_PRODUCTION:
        print("=" * 50)
        print("生产模式启动")
        print("前端应用: http://127.0.0.1:80")
        print("API文档: http://127.0.0.1:80/docs")
        print("=" * 50)
    else:
        print("=" * 50)
        print("开发模式启动")
        print("后端API: http://127.0.0.1:8000")
        print("API文档: http://127.0.0.1:8000/docs")
        print("前端应用: http://localhost:3000 (需要单独启动)")
        print("=" * 50)
    yield

app = FastAPI(title="GPU QC 查询系统", lifespan=lifespan)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Vite开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(routes.router)

if IS_PRODUCTION:
    # 生产环境：挂载构建后的静态文件
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """为SPA提供所有非API路由的index.html"""
        if not full_path.startswith("api/"):
            return FileResponse("frontend/dist/index.html")
        return {"error": "Not found"}
else:
    # 开发环境：不挂载静态文件，由Vite开发服务器提供
    pass

# 直接通过 python -m app.main运行
if __name__ == "__main__":
    import uvicorn
    if IS_PRODUCTION:
        # 生产模式：使用80端口
        uvicorn.run("app.main:app", host="0.0.0.0", port=80)
    else:
        # 开发模式：使用8000端口
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
