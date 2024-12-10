This application contains most of the code (and data migrations) for running
different instances of the Unity League website from a single database.

This is required as we want to be able to share informations between the EUL
and the SUL, in particular, events from the SUL are integrated into the EUL,
but not the other way around (as of 2025 season).

## Adding a new site-specific information

All the site-specific information (e.g. contact email) live in the
`multisite.models.SiteSettings` model. In order to simplify programming, all
fields of that model must be mandatory (i.e., no `blank`), so that we can
always assume we have the relevant piece of information.

In order to add a field to the database, first edit `multisite/models.py`, add
your relevant field, and then you will need to make a data migration that first
adds the field as not required, adds the data, then marks it as required. see
`multisite/migrations/0003_sitesettings_contact_email.py` for an example of how
this is done.
