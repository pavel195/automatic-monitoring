FROM node:20-alpine

WORKDIR /app/frontend

COPY frontend/monitoring-ui/package*.json ./
RUN npm install

COPY frontend/monitoring-ui .

EXPOSE 4200

CMD ["npm", "run", "start"]

