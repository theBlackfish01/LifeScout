FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for weasyprint and other libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose chainlit port
EXPOSE 8000

# Command to run chainlit
CMD ["chainlit", "run", "app.py", "-w", "--port", "8000", "--host", "0.0.0.0"]
