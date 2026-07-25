# Use an official lightweight Node.js image
FROM node:22-alpine

# Set working directory
WORKDIR /app

# Copy dependency files first (better Docker cache)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend source
COPY . .

# Expose Vite development server port
EXPOSE 5173

# Start the development server
CMD ["npm", "run", "dev", "--", "--host"]