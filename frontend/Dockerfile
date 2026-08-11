# LegalEye 前端镜像：构建 + nginx 静态托管
FROM node:22-alpine AS build

WORKDIR /app

# 安装 pnpm 并安装依赖（锁文件冻结）
RUN npm install -g pnpm@11.21.0
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# 构建
COPY . .
RUN pnpm build

# 运行阶段：nginx 托管静态资源 + 反向代理后端
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
