# Frontend development image. Build context is the repository root:
#   docker build -f docker/frontend.Dockerfile -t dataguardian-frontend .
#
# This runs the Vite dev server. A production variant (build + static serve)
# gets added when the app is ready to deploy.
FROM node:22-alpine

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
