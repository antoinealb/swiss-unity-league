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

RUN /app/manage.py collecstatic

EXPOSE 8000

CMD ["gunicorn", "--bind", ":8000", "--workers", "1", "mtg_championship_site.wsgi:application"]
