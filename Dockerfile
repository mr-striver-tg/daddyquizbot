# Use slim python base
FROM python:3.12-slim

WORKDIR /app

# Copy files
COPY main.py .
COPY quiz_template.html .

# Install dependencies
RUN pip install --no-cache-dir python-telegram-bot==20.6

# Make writable directories for Koyeb
RUN mkdir -p /tmp/data /tmp/exports

# Run bot
CMD ["python", "main.py"]
