FROM python:3.10-alpine

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies
RUN pip install --no-cache-dir fastmcp pyyaml flask markdown-it-py beautifulsoup4 numpy scikit-learn

# Copy application files
COPY utils/ /app/utils/
COPY enhanced_mcp_server.py /app/

# Define the tutorials directory as a volume
VOLUME /tutorials

# Expose MCP server port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000
ENV TUTORIAL_DIR=/tutorials

# Entry point
CMD ["python", "enhanced_mcp_server.py", "--tutorial-dir", "/tutorials"] 