FROM python:3.10

RUN mkdir -p /app
WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app

RUN /app/manage.py collectstatic --no-input

# HTTP endpoint
EXPOSE 8000

# Metrics endpoint, one per worker
EXPOSE 8001
EXPOSE 8002
EXPOSE 8003

CMD ["gunicorn", "--bind", ":8000", "--workers", "3", "mtg_championship_site.wsgi:application"]
