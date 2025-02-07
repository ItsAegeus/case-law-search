# Use a Node.js base image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package.json and install dependencies
COPY package.json ./
RUN npm install

# Copy all React frontend files (adjust if needed)
COPY . ./

# Build the React app
RUN npm run build

# Expose the frontend port
EXPOSE 3000

# Serve the built React app
CMD ["npx", "serve", "-s", "build", "-l", "3000"]