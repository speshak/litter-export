FROM python:3.12.0-alpine

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        pipenv

RUN mkdir /app
WORKDIR /app

COPY Pipfile Pipfile.lock *.py /app/

RUN pipenv install --system --deploy --ignore-pipfile

EXPOSE 8000
ENTRYPOINT ["python", "litterbot-export.py"]
