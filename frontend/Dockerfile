FROM nginx:1.27-alpine

COPY frontend/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY frontend/nginx/10-generate-runtime-config.sh /docker-entrypoint.d/10-generate-runtime-config.sh
COPY frontend/*.html /usr/share/nginx/html/
RUN chmod +x /docker-entrypoint.d/10-generate-runtime-config.sh

EXPOSE 8080
