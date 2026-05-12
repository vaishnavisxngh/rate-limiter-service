# build
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first — Docker caches this layer if requirements haven't changed,
# which speeds up subsequent builds significantly.
COPY requirements.txt .

# Install dependencies (--no-cache-dir keeps the image smaller)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Tell Docker that this container listens on port 8000
EXPOSE 8000

# Start the server.
# --host 0.0.0.0 is required inside Docker so the port is reachable from outside the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
