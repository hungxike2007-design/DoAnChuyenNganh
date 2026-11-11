FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DB_TYPE=sqlite DATABASE_PATH=data/revenue_system.sqlite HOST=0.0.0.0 PORT=8000
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ unixodbc unixodbc-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "main.py"]
