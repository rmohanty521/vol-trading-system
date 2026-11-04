FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY scripts ./scripts
RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1
CMD ["python", "scripts/scheduler.py", "--paper"]
