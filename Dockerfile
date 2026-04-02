FROM python:3.10-slim

WORKDIR /app

RUN pip install uv

COPY . /app

RUN uv sync

EXPOSE 7860

CMD ["uv", "run", "python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]