FROM node:22-alpine AS build

WORKDIR /app/ui-web

COPY ui-web/package.json ./package.json
COPY ui-web/tsconfig.json ./tsconfig.json
COPY ui-web/tsconfig.node.json ./tsconfig.node.json
COPY ui-web/vite.config.ts ./vite.config.ts
COPY ui-web/index.html ./index.html
COPY ui-web/public ./public
COPY ui-web/src ./src

RUN npm install
RUN npm run build

FROM nginx:1.27-alpine

COPY docker/ui-web.nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/ui-web-entrypoint.sh /docker-entrypoint.d/40-runtime-config.sh
COPY --from=build /app/ui-web/dist /usr/share/nginx/html

RUN chmod +x /docker-entrypoint.d/40-runtime-config.sh

EXPOSE 8080
