FROM nginx:1.27-alpine

COPY frontend/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY frontend/*.html /usr/share/nginx/html/

EXPOSE 8080
