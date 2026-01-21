FROM node:20-alpine AS build

WORKDIR /app
COPY fronted/package.json fronted/package-lock.json /app/
# Use `npm install` instead of `npm ci` to avoid hard failures when the lockfile
# is slightly out of sync in release ZIPs. This makes "one-click deploy" more robust.
RUN npm install --no-audit --no-fund
COPY fronted /app
RUN npm run build

FROM nginx:1.27-alpine
COPY fronted/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
