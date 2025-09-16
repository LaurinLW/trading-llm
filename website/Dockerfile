FROM node:alpine AS build
ARG BACKEND_URL
ARG WEBSOCKET_URL
ENV BACKEND_URL=$BACKEND_URL
ENV WEBSOCKET_URL=$WEBSOCKET_URL

WORKDIR /app

COPY package*.json ./
COPY vite.config.js ./
RUN npm install

COPY website ./website/
RUN npm run build

FROM caddy:alpine

COPY --from=build /app/website/dist /usr/share/caddy/

COPY website/Caddyfile /etc/caddy/Caddyfile

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile"]