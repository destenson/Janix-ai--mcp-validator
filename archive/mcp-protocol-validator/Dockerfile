FROM python:3.11.8-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mcp_validator.py .
COPY tests/ ./tests/
COPY schema/ ./schema/
COPY pytest.ini .
COPY conftest.py .

# Create entrypoint
ENTRYPOINT ["python", "mcp_validator.py"]

# Default command line arguments
CMD ["--help"] 