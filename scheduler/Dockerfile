FROM python:3.13.1-slim

WORKDIR /app

COPY scheduler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python","-m","scheduler.scheduler" ]
