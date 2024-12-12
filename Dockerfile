FROM python:3.12

RUN mkdir -p /app
WORKDIR /app

# Install latex for invoices
RUN apt-get update && apt-get install -y \
    # keep-sorted start
    libgdal-dev \
    texlive \
    texlive-latex-extra \
    texlive-latex-recommended \
    texlive-science \
    # keep-sorted end
  && rm -rf /var/lib/apt/lists/*

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app

RUN /app/manage.py collectstatic --no-input

# Update Oracle cards from scryfall
RUN /app/manage.py migrate --database oracle && /app/manage.py scryfall_import

# Download IP database file
RUN /app/manage.py download_ipdb

# HTTP endpoint
EXPOSE 8000

# Metrics endpoint, one per worker
EXPOSE 8001
EXPOSE 8002
EXPOSE 8003

CMD ["gunicorn", "--bind", ":8000", "--timeout", "60", "--workers", "8", "swiss_unity_league_site.wsgi:application"]
