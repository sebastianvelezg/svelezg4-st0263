FROM python:3.8-slim

WORKDIR /usr/src/app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 4001

ENV SERVER_URL=localhost
ENV SERVER_PORT=4001

CMD ["python", "./Server.py"]
