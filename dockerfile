FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install flask python-dotenv requests

EXPOSE 7007

CMD ["python", "main.py"]