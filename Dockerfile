# Use an official Python runtime as the base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app

# Expose port
EXPOSE 5001

# Define environment variable
ENV FLASK_APP=app.py

# Run app.py with gunicorn on dynamic or default port 5001
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5001} app:app"]