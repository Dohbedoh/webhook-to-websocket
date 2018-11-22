FROM ubuntu:16.04
EXPOSE 8080

RUN apt-get update && apt-get install -y python
#RUN pip install git+https://github.com/dpallot/simple-websocket-server.git
RUN apt-get install -y python-pip python-dev build-essential
RUN pip install tornado ddtrace[opentracing]

ENV DATADOG_AGENT_APM_HOST "172.17.0.1"
ENV DATADOG_AGENT_APM_PORT "8126"

ADD ./app /app

CMD ddtrace-run python /app/webhook.py
