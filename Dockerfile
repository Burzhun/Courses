FROM python:3.7

ENV PYTHONUNBUFFERED=1

RUN apt update && apt install -y \
    postgresql-client \
    gettext \
    ffmpeg

RUN pip install uwsgi pipenv

WORKDIR /opt/coursify
COPY Pipfile Pipfile.lock ./

RUN pipenv install --system --deploy --dev

COPY . .

RUN cd docs && make html

# This is a special case. We need to run this script as an entry point:
COPY ./entrypoint.sh /entrypoint.sh

RUN chmod +x "/entrypoint.sh"
ENTRYPOINT ["sh", "/entrypoint.sh"]

EXPOSE 80
ENV PORT 80

CMD ["uwsgi", "./coursify/uwsgi.ini"]
