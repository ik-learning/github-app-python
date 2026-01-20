# docker build -f services/workers/blackduck/Dockerfile -t worker-blackduck .
# docker run --rm -it -p worker-blackduck
FROM blackduck-deps:latest

RUN printf "build_time=%s\n" "$(date -u +%d/%m/%Y_%H:%M)" > settings.ini

ARG APP_HOME=/app
WORKDIR $APP_HOME

COPY . ${APP_HOME}/
EXPOSE 8080

# https://www.geeksforgeeks.org/python/fastapi-uvicorn/
CMD ["pipenv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--reload"]
