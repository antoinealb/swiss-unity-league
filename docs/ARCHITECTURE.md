---
title: SUL website architecture
author: Antoine Albertelli, Leonin League
---

# Intro

The SUL website is written in Python with the [Django](https://www.djangoproject.com/) web framework.
We make extensive use of ([class based views](https://docs.djangoproject.com/en/5.0/topics/class-based-views/), so if you are not familiar with them, you can read about them [in the tutorial](https://docs.djangoproject.com/en/5.0/intro/tutorial04/#use-generic-views-less-code-is-better).

Generally the website is rendered fully server side, with no client side Javascript needed.
The only exception is the "Upcoming events" view, which use client-side rendering to filter events quickly.
For this, we use a small js framework called [Alpine](https://alpinejs.dev/).

The website offers an API at `unityleague.ch/api`, which you can explore within a browser.
It is based on Django Rest Framework.

# Production environment

The website runs in Docker on `server01.fsn.antoinealb.net`, a server owned by Antoine and running multiple other things.

Deployment occurs directly from Gitlab.
On every push to `master`, tests are run, the docker image is built, tagged (`antoinealb/league:latest`) and pushed.
The image is then pulled on the web host, and the service is then restarted.
Overall the process takes about half an hour between your commit landing on master and it being visible on the website.

We use SQLite as our database which should be plenty fast for our needs, and is very simple to use (everything is in a single file).
To keep things simple, the database is also used to store user-uploaded files (although there is a cache in front).
Database backups occur daily, ask Antoine or Jari if you need access.

There is a playground environment for testing at `https://playground.unityleague.ch`.
It is deployed at the same time as the production one, and uses a copy of its database.

# Database tables

## EventOrganizer

This model represents an instance of a tournament organizer (a group, not a person).
It is used to associate events with organizers and to let them customize their branding by uploading logos and descriptions.

Note that each EventOrganizer is associated with a single login credential through a one-to-one relationship with the use model.
This means that each organizer receives a single username and password to access their events.
It also means this model does not store any authentication information but delegates it all to the authentication app.

We store the following information about tournament organizers.
Note that most of it can be edited by the organizer themselves through their profile settings.
We can kind-of trust them (for example we can assume they will not upload abusive content), but we still need to validate what they do.

- Name (e.g. `Leonin League`)
- Email address for contact (e.g., for invoicing)
- Image, which will be displayed on the home page (i.e. for their logo).
- Their default Address, which will be added to events they create.
- Link to a `django.contrib.auth.models.User` or similar, used for authenticating them.

## Event

This model represents a single tournament that players can enter.
In some cases, what we would consider a single event has multiple Event, as in the case of Swiss Magic Master having both a limited and legacy tournament at the same time, in the same room

Events contain quite a few informations at once, so let's start with what is required simply to communicate about the event:

- Name (e.g. "Modern 1k by Leonin League")
- Format (e.g. Modern, Legacy)
- Organizer, a foreign key to an `EventOrganizer`
- The date of the event
- The start time and estimated end time. While the date is required, the times are not.
- The event description, which can contain some formatting in HTML.
- URL where players can read more about it, buy tickets and so on.
- An image that will be displayed on the event's page for advertisement.
- A foreign key to the event's location.
- The category of the event (e.g. Regional), also used to display the event in the calendar.

The following fields will generaly be available only after the event has passed:

- URL where decklists / metagame of the event can be found.

Finally, the SUL rules places some restrictions on event upload, and we have some validation in-place to enforce those.
However, there are sometimes good reasons to ignore those restrictions and this is controlled through the `Event` field as well.
This can only be controlled by a SUL staff member through the admin panel.

- `results_validation_enabled` is a boolean allowing us to disable the validation of results for a single tournament.
- `edit_deadline_override`, which allow us to extend the deadline for result submission for a single event.

## Player

This table represents a single player in the tournament.
Player go to tournaments, have results, and end up on the leaderboard.

We don't store a lot of information about players.
Only their name[^whyname], email addresses in some case (to contact for the invitational).
They also have an id, used to implement the relationship with events.

There is also a field to indicate if a player should be hidden from the leaderboard.
This is used as we have some "virtual" players, for example Eventlink will create an "Unknown" player that we can hide this way.

[^whyname]: We store names as a single piece of texet, instead of splitting it into first and last names.  This is because names don't always have the structure we expect. See [https://www.kalzumeus.com/2010/06/17/falsehoods-programmers-believe-about-names/](https://www.kalzumeus.com/2010/06/17/falsehoods-programmers-believe-about-names/).

## PlayerAlias

This table is very related to the `Player` table above.
Sometimes, player will enter a tournament under a nickname, for example `YellowHat` instead of `Gabriel Nassif`, but still would like the score to go to their real identity.

To do so we can create player aliases which contain a nickname and point to a `Player`.
When uploading scores, if there is a `PlayerAlias` for a given name, we will use this instead of creating a new player.

## Result

This table is perhaps the most important one to implement the SUL.
It contains a link between Event and Player and as such, represents how a given person performed in a given tournament.
Computing the leaderboard consists then of iterating over all Result, accumulating points for players as we go.

Result is used as the intermediate model for a [Django ManyToMany relationship](https://docs.djangoproject.com/en/4.0/topics/db/models/#intermediary-manytomany).
This makes it easy to access results both for a given player and for a given event.

It contains the following fields:

- `win_count`, `draw_count`, `loss_count` and `points`, which represent the performance in the swiss portion of a tournament.
    This is what we use to calculate SUL points[^pointsmigration].
- `ranking` is how high a player scored in the Swiss, used to display standings for one event.
    We cannot simply sort it based on points, as there are also tie-breakers, so instead we take it from the uploaded results.
- We store the `deck_name` and `decklist_url`, which can be populated on result upload to allow people to explore the metagame from our event results page.

[^pointsmigration]: We used to score results as `points` only, but migrated to win, loss, draw later.
Points are still written in the database but should not be used anymore.
There is a field indicating if a result was migrated from points to W/L/D (by estimating standings), or if it was natively written.
