FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for chromadb/numpy
RUN apt-get update && apt-get install -y \
    gcc \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (exclude .gradio, __pycache__, .env)
COPY --exclude=['.gradio','__pycache__','.env'] . .

# Set port for HuggingFace Spaces
ENV PORT=7860
EXPOSE 7860

# Run the application
CMD ["python", "app.py"]