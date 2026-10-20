# Frontend Docker image — SvelteKit Node server on port 3000
FROM node:22

WORKDIR /app

# Enable pnpm via corepack.
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy package manifests and install dependencies.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

# Copy the rest of the app and build.
COPY . .
RUN pnpm build

# Runtime environment variables.
ENV NODE_ENV=production
ENV API_URL=http://backend:8005
ENV PORT=3000

EXPOSE 3000

CMD ["node", "build/index.js"]
