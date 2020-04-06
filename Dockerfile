FROM python:3.8-alpine
COPY . /app
WORKDIR /app
CMD ["python", "server.py"]