FROM node:22-alpine AS deps
WORKDIR /web
COPY package.json ./
RUN npm install
FROM node:22-alpine AS build
WORKDIR /web
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY --from=deps /web/node_modules ./node_modules
COPY . .
RUN npm run build
FROM node:22-alpine
WORKDIR /web
ENV NODE_ENV=production
COPY --from=build /web/.next/standalone ./
COPY --from=build /web/.next/static ./.next/static
COPY --from=build /web/public ./public
EXPOSE 3000
CMD ["node","server.js"]

