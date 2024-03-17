# Unity League Ranking website

## Running the code locally

First, you need to install the dependencies. The example below shows how to do
that in a virtual environment, which is recommended to isolate your development
environment from your system.

### Installing dependencies

```shell
python3 -m venv env
env/bin/pip install -r requirements.txt
```

this is only needed once, however, when working with the code, make sure that
your virtual environment is correctly activated with the following command:

```shell
# Start the dev environment with the modules you installed above
# This must be run in every shell you want to work in.
source /env/bin/activate
```

### Running the unit tests

```shell
./manage.py test --exclude-tag=latex
```

Note that here we are removing the tests that include Latex (PDF generator), as
generating PDF is quite slow. If you are testing invoice generation, you can
ommit `--exclude-tag` from your command.

### Creating the database

The next step is to create the database, and to apply any pending migrations.

```shell
./manage.py migrate
```

### Creating an admin user

```shell
./manage.py createsuperuser
```

You might then want to create a Tournament Organizer profile for the superuser
by going to the admin panel once your website is running.

### Generating fake data

This command just generates a few fake tournaments, with fake players and fake TOs for testing the website without having access to the real database.

```shell
./manage.py generatedata
```

### Running the dev server

```shell
./manage.py runserver
```

### Setting up pre-commit hooks

1. First, install [pre-commit](https://pre-commit.com/), you can do it with `pip install pre-commit` or use your package manager.
2. Then, run `pre-commit install`
3. Now, everytime you run `git commit`, code formatting will be enforced and fixed automatically.
