FROM python:3.10

WORKDIR /app

COPY requirements.txt /app/

RUN apt update && apt upgrade -y

COPY . .

RUN pip3 install -r requirements.txt

COPY . /app

CMD python bot.py
