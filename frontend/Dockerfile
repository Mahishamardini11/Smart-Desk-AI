# syntax=docker/dockerfile:1
FROM node:20-alpine
WORKDIR /app

# Copy manifests first so npm install layer is only invalidated when deps change.
COPY package*.json ./
# BuildKit cache mount: npm cache persists between builds.
RUN --mount=type=cache,target=/root/.npm \
    npm install --prefer-offline

COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
