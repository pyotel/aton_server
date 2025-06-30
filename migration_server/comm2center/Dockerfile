# Use an official Python 3 image as a parent image
FROM python:3.13.0

# Set the working directory inside the container
WORKDIR /app

# Copy your Python script into the container
COPY . .

# Install Python dependencies
RUN pip3 install -r /app/requirements.txt

# Run your script
CMD ["python", "comm2center.py"]
