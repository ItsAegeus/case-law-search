# Use an official Node.js image with Alpine (lightweight)
FROM node:18-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json first (for caching dependencies)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy all project files
COPY . .

# Build the React app
RUN npm run build

# Expose the port (default for static sites)
EXPOSE 3000

# Serve the built app using a simple static server
CMD ["npx", "serve", "-s", "build", "-l", "3000"]