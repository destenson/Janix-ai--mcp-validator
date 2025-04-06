FROM node:22.12-alpine AS builder

WORKDIR /app

# Copy the project files
COPY src/filesystem/ /app/
COPY tsconfig.json /app/tsconfig.json

# Ensure the tsconfig.json is correctly set up for the filesystem project
RUN echo '{"compilerOptions":{"target":"ES2022","module":"Node16","moduleResolution":"Node16","strict":true,"esModuleInterop":true,"skipLibCheck":true,"forceConsistentCasingInFileNames":true,"resolveJsonModule":true,"outDir":"dist"},"include":["src/**/*"],"exclude":["node_modules"]}' > /app/tsconfig.json

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