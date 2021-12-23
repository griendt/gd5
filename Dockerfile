FROM python:3.10-slim

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app

WORKDIR /app

CMD ["tail", "-f", "/dev/null"]
