@echo off
echo.
echo ===================================================
echo        LegalEye 完整系统启动脚本
echo ===================================================
echo.

echo 正在启动依赖服务...
echo.

REM 启动数据库
echo 启动 PostgreSQL 数据库...
start "" "cmd" /k "docker run -d --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16"

timeout /t 3 >nul

REM 启动 Redis
echo 启动 Redis 服务...
start "" "cmd" /k "docker run -d --name redis -p 6379:6379 redis:alpine"

timeout /t 3 >nul

echo.
echo 正在启动后端服务...
echo.

REM 启动后端
start "" "cmd" /k "cd d:\Pycharm\python project\legaleye\backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 2 >nul

echo.
echo 正在启动前端服务...
echo.

REM 启动前端
start "" "cmd" /k "cd d:\Pycharm\python project\legaleye\frontend && pnpm run dev"

echo.
echo ===================================================
echo 系统启动完成！
echo 后端服务: http://localhost:8000
echo 前端服务: http://localhost:5173
echo ===================================================
echo.

echo 请等待服务启动完成，然后在浏览器中访问:
echo http://localhost:5173
echo.

pause