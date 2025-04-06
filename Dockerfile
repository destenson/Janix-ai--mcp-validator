FROM node:22.12-alpine AS builder

WORKDIR /app

# Copy files from the current directory
COPY . /app

# Install dependencies
RUN --mount=type=cache,target=/root/.npm npm install

# Build the project
RUN npm run build

FROM node:22-alpine AS release

WORKDIR /app

COPY --from=builder /app/dist /app/dist
COPY --from=builder /app/package.json /app/package.json
COPY --from=builder /app/package-lock.json /app/package-lock.json

ENV NODE_ENV=production

RUN npm ci --ignore-scripts --omit-dev

ENTRYPOINT ["node", "/app/dist/index.js"] 