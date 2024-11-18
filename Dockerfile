# Base image
FROM python:3.10-slim

RUN apt update && apt install -y \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

RUN python -m venv .venv

RUN /bin/bash -c "source .venv/bin/activate"

# Install necessary packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script into the container
COPY check.py .

# # Command to run the script
CMD ["python", "check.py"]