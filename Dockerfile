# Use Node.js base image
FROM node:18-alpine

# Set working directory inside the container
WORKDIR /app

# Copy package.json and install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy the rest of the app
COPY frontend ./

# Build the React app
RUN npm run build

# Expose the frontend port (React uses 3000)
EXPOSE 3000

# Serve the frontend using a static server
CMD ["npx", "serve", "-s", "build", "-l", "3000"]
