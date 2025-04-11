# Use an official Python runtime as a parent image
FROM python:alpine

# Step 3: Copy only the requirements file first (to cache pip install)
COPY requirements.txt .

# Step 4: Install Python dependencies (this layer is cached unless requirements.txt changes)
RUN pip install --no-cache-dir -r requirements.txt

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Run the app
CMD ["python", "main.py"]
