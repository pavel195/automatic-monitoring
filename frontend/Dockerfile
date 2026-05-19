FROM node:20-alpine

WORKDIR /app/frontend

RUN apk add --no-cache chromium
ENV CHROME_BIN=/usr/bin/chromium-browser

COPY frontend/monitoring-ui/package*.json ./
RUN npm install

COPY frontend/monitoring-ui .

EXPOSE 4200

CMD ["npm", "run", "start"]
