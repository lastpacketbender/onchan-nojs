FROM python:latest

WORKDIR /app
ADD . /app
RUN pip install -r requirements.txt
EXPOSE 8080
CMD ["python3", "/app/service.py"]
