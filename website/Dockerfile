FROM node:alpine AS build

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