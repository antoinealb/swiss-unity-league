# Unity League Ranking website

## Running the code locally

First, you need to install the dependencies. The example below shows how to do
that in a virtual environment, which is recommended to isolate your development
environment from your system.

### Installing dependencies

```shell
$ python3 -m venv env
$ source env/bin/activate
$ pip install -r requirements.txt
```

this is only needed once, however, when working with the code, make sure that
your virtual environment is correctly activated.

### Running the unit tests

```shell
$ ./manage.py test
```

### Creating the database

The next step is to create the database, and to apply any pending migration.

```shell
$ ./manage.py migrate
```

### Creating an admin user

 ```shell
$ ./manage.py createsuperuser
```

You might then want to create a Tournament Organizer profile for the superuser
by going to the admin panel once your website is running.

### Generating fake data

```shell
$ ./manage.py generatedata
```

### Running the dev server

```shell
$ ./manage.py runserver
```
