# Decklist upload for SUL website

## Goals

- Store decklists submitted for tournament
- Allow player to edit their decklist and have the confirmation their list is edited.
- Allow judges & streamers to access list.
- Allow publication of decklist at the end of the tournament or for the open decklist portion.
- Support TOs who are members of the SUL for collecting decklists.

## Non-goals

- Be a generic deckbuilding tool.
    There is already excellent deckbuilding software such as MoxField, the world does not need another one.
- Be a collection management tool.
- Determine the legality of submitted decklists.
- Store history of decklists.
- Support TOs who are not in the SUL.

# Database Models

## Collection

This model represents a group of decklists that are collected at the same time and are grouped.
For example, one group could be "Decklists for the Modern portion of the 2024 trial".

Groups have the following attributes:

- `name` (CharField): Human readable name of the group.
- `deadline` (DateTimeField): Time until which new decklists can be uploaded or edited.
- `decklists_published` (BooleanField): Boolean indicating whether or not the decklists should be publicly visible now.
- `event` (Foreignkey to `championship.model.Event`).
    The event associated with the decklist.
    We consider that `event.organizer` is the owner of the `Collection`.

Why have a separate `Collection` model rather than attach decklists to `Event` ?

- The `Event` model already has a lot of informations in it.
    Separation of concern is at play here.
- The majority of `Event`s do not collect decklists.
- Some events would have several `Collection`, for example because they have several formats.
- Some organizers might want to set the deadline to one hour before the event, or 10 min, etc.

## Decklist

- `id` (UUIDField): The identifier of the decklist used as primary key.
    This field will use `default=uuid.uuid4` to generate random UUIDs for each record.
- `collection` (ForeignKey to `Collection`): The collection for which this list was uploaded.
- `player` (ForeignKey to `championship.models.Player`): Link to the player who submitted the decklist.
- `archetype` (CharField): Player-submitted name for the decklist.
- `last_modified` (DateTimeField): When the decklist was last modified (using Django's `auto_now` attribute).
- `decklist` (TBD): The actual decklist, stored in a convenient format.

Why do we use an UUID for the decklist primary key, where the rest of the website uses an incrementing counter for primary keys?
Using a random key allows us to make decklists URLs unguesseable, and that only the player who uploaded the decklist would know its id.
This means, in turn, that we don't need to authenticate players when they want to edit their decklist; we can assume that the person who views the page for a decklist is authorized to edit it.
Of course this changes once a Collection is published, but at this point we disable edits for the decklist.

An URL for a sample decklist (view & edit) would be `https://unityleague.ch/decklist/442ab532-2d06-4ba9-bb75-e6992d4b8e4c`.

Just how small of a chance is it to find a random UUID?
Let's assume decklists are uploaded one week before the tournament.
The attacker could sustaing ~40 QPS to the website (what SUL can serve at the moment).
An UUID4 has 122 bits of randomness.
This means the probability of finding a collision is `(40 * 60 * 60 * 24 * 7) / (2**122) = 4e-30`.
This is more than secure for our application.

# Views

## Collection details

- View a collection as an anonymous user.
    * Display the name & deadline of the group.
    * Display a list of players who uploaded their decklist, as well as the last modification time of their decklists.
        Allow sorting that list by player name or last modification time.
    * If before the deadline, display a form to add your decklist.
    * If the logged in user is the owner of the Collection, display links to the decklists.
    * If the Collection is marked as `published`, display links to the decklists.

## List my Collections

- Show all collections belonging to the logged in user, sorted by descending deadline.
- Display link to go view each collection.

## View & edit a single decklist

- If the related collection's deadline is not reached: forms to allow edition.
- If the logged in user is the owner of the Collection, forms to allow edition
- Visual view showing artwork, and potentially sorting cards.
- Warnings if there are unknown cards.

The validation of a single decklist will probably occur in this view.
The validation can be done using [MTGJson](https://mtgjson.com/)'s dataset.
The dataset would be loaded in-memory and used from there.
The same data can be used to provide an autocomplete.

## API Views

None needed.
