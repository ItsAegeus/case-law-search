# Use Node.js base image
FROM node:18-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json first (for better caching)
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy all React project files
COPY . ./

# Build the React app
RUN npm run build

# Expose the frontend port
EXPOSE 3000

# Serve the React app using "serve"
CMD ["npx", "serve", "-s", "build", "-l", "3000"]