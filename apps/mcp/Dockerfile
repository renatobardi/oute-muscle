FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .

RUN pip install -e ".[dev]" --no-cache-dir

COPY src/ ./src/

EXPOSE 8080

CMD ["python", "-m", "src.main"]
