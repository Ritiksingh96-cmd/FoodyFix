# Use official lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port 8080 (standard for Google Cloud Run)
EXPOSE 8080

# Command to run the application
CMD ["python", "main.py"]
