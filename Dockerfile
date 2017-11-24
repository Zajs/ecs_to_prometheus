FROM python:2.7-alpine

ENV AWS_REGION=us-east-1 ECS_CLUSTERS=production PATH_TO_SAVE=/app/services

ADD src/ /app/
ADD requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt && chmod +x /app/scrap_ecs.py

CMD /app/scrap_ecs.py