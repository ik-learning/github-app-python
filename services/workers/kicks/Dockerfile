# docker build -f services/workers/kicks/Dockerfile -t worker-kicks .
# docker run --rm -it -p 8000:8000 worker-kicks
FROM kicks-deps:latest

RUN printf "build_time=%s\n" "$(date -u +%d/%m/%Y_%H:%M)" > settings.ini

ARG APP_HOME=/app
WORKDIR $APP_HOME

COPY . ${APP_HOME}/
EXPOSE 8080

CMD ["pipenv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--reload"]
