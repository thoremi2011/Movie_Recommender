# Use Python 3.9 base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements files first (to leverage Docker cache)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Copy and grant permissions to startup script
COPY start.sh .
RUN chmod +x start.sh

# Expose ports used by Gradio (7860) and FastAPI (8000)
EXPOSE 7860 8000

# Run startup script
CMD ["./start.sh"]
