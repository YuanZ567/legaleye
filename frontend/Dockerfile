# LegalEye 前端镜像：nginx 托管静态资源 + 反向代理后端
# 构建前需在本地先执行 pnpm build（生成 dist/）
FROM nginx:alpine
COPY dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
