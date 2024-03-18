---
title: A design for a Swiss ATP-style championship system
author: Antoine Albertelli, Leonin League
---

# User journeys

## Required

* Upload tournament results
    - Only for persons logged in as TOs.
    - SHould we allow "draft" as in you can pause and come back to data input later ?
    - Input from Excel ?
* Look up the ranking for a given format
* Look up the overall ranking
* Look up a player history
* View a list of the last N tournaments (or all tournaments from the year)
* Lookup the result of a particular tournament
* Login (for organizers)
* Create a player
    - Should we do it automatically on unknown player ?
    - How do we handle typos and other mistakes where we want to merge two players?
        - Originally, can be done with the Django admin panel
* Compute the total ranking of everyone
    - Ondemand, cron job, or on tournament changes ?
* Report a bug
    - Can be done through Github / Gitlab
    - But perhaps a better function is needed for players who would want to
      correct their name and so on.
* Content pages:
    - Explain the ranking like [this](https://azcanta-tournaments.ch/mtgr/).

## Nice to have

* Import from Eventlink
* Import from Aetherhub
* Show a calendar with upcoming events
    - Expose it as iCal
* Social login / login with Google
* Penalty reporting ?

## Possible extensions (not in scope)

- Register players through the website
- Handle tournament pairings through the website
- Handle inputting results through the website

# Database entitites

## Player

- Name
- Many to Many relationship with events through an EventResult

## Organizer

- Name (Leonin League, KSVZ, etc.)
- Contact email
- Foreign key or whatever to associate it with a login account.

## Event

- Foreign Key to TO
- Date
- Name
- URL
- Event category (MTGR100, 250, 500, 1000) -> uses an enum
- Event format (Limited, Modern, Legacy) -> enum
- Ranking type (ROUNDS or RANKED)
- Number of rounds (only used if ROUNDS)

## Event Result

Used as an intermediate model for the Player <-> event relationship.
See https://docs.djangoproject.com/en/4.1/topics/db/models/#intermediary-manytomany

- Ranking (used if RANKED)
- Points (used if ROUNDS)
    - Perhaps better to input them with the good W-L-D format.

# Implementation strategy

* Based on Django
* Initially, a lot of the flows can be done through the Django admin panel
    - Fixing error in data
    - Creating events
    - Merging players (require a playbook on how to do this)
    - Create tournament organizer

Frontend honestly sucks. We might need someone with Frontend skills to work on that.
In the meantime, it is going to look a lot like a normal twitter bootstrap website.
We can perhaps change the colorscheme later, if not too hard to do.

Database can be SQLite for now, making backups super easy. We *must* have backups.

Deployment will be done using Docker + running on Antoine's server.
We can then use Gitlab CI to build the image and restart the server.
