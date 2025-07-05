# Use official Python image
FROM python:3.10

# Install system dependencies required by Playwright
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnspr4 \
    libnss3 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libasound2 \
    wget \
    && apt-get clean

# Set workdir
WORKDIR /app

# Copy your code
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps

# Expose port
EXPOSE 8000

# Run FastAPI app with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
