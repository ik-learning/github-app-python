# docker build -t githubapp .
# docker run --rm -it -p 8080:8080 githubapp
FROM python:3.14

ARG APP_HOME=/app
WORKDIR $APP_HOME

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY Pipfile Pipfile.lock ${APP_HOME}/

RUN pip install --root-user-action ignore pipenv
RUN pipenv install --deploy --ignore-pipfile
RUN pip freeze

COPY . ${APP_HOME}/
EXPOSE 8080

WORKDIR ${APP_HOME}/src

# https://www.geeksforgeeks.org/python/fastapi-uvicorn/
CMD ["pipenv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--reload"]
