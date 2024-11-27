# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import dataclasses

from django.db import migrations, models

from parsita import (
    ParserContext,
    eof,
    failure,
    lit,
    longest,
    opt,
    reg,
    repsep,
    success,
    until,
)

import decklists.models


# copied from decklists/parser to maek sure it does not change.
@dataclasses.dataclass
class ParsedDecklistEntry:
    qty: int
    name: str


@dataclasses.dataclass
class ParsedDecklist:
    mainboard: list
    sideboard: list


def non_null_length(*args):
    if not args or args[0] == "":
        return failure("Should not be null length")
    return success(args[0])


def _convert_mtgo_parse_result(result):
    main = [ParsedDecklistEntry(r[0], r[1]) for r in result[0]]
    side = [ParsedDecklistEntry(r[0], r[1]) for r in result[1]]
    return ParsedDecklist(mainboard=main, sideboard=side)


def _convert_mwdeck_result(result):
    # Discard comments
    result = [r for r in result if isinstance(r, list)]
    main = [ParsedDecklistEntry(r[1], r[2]) for r in result if not r[0]]
    side = [ParsedDecklistEntry(r[1], r[2]) for r in result if r[0]]
    return ParsedDecklist(mainboard=main, sideboard=side)


class DecklistParser(ParserContext, whitespace=r"[ \t]*"):  # type: ignore
    # Generic utility functions
    newline = longest(lit("\r\n"), lit("\n"), lit("\r"))
    until_end_of_line = until(newline | eof) >= non_null_length
    integer = reg(r"[0-9]+") > int
    card = until_end_of_line > (lambda s: s.rstrip())

    # Magic Workstation (mwdeck) format
    mwdeck_set = reg(r"[0-9A-Z]+")
    mwdeck_sideboard = lit("SB:")
    mwdeck_card = (
        (opt(mwdeck_sideboard) > (lambda s: bool(s)))
        & (integer << lit("[") << opt(mwdeck_set) << lit("]"))
        & card
    )
    mwdeck_comment = lit("//") >> until_end_of_line
    mwdeck_line = mwdeck_card | mwdeck_comment
    mwdeck_deck = (
        repsep(mwdeck_line, newline) << opt(newline)
    ) > _convert_mwdeck_result

    # MTGO / txt format
    line = integer & card
    mtgo_sideboard = opt(lit("Sideboard")) & newline
    mtgo_part = repsep(line, newline) << opt(newline)
    mtgo_deck = ((mtgo_part << mtgo_sideboard) & mtgo_part) > _convert_mtgo_parse_result

    # Put together
    deck = mwdeck_deck | mtgo_deck


def merge_content(apps, schema_editor):
    Decklist = apps.get_model("decklists", "Decklist")
    db_alias = schema_editor.connection.alias
    for d in Decklist.objects.using(db_alias).all():
        d.content = f"{d.mainboard}\n\nSideboard\n{d.sideboard}"
        d.save()


def unmerge_content(apps, schema_editor):
    Decklist = apps.get_model("decklists", "Decklist")
    db_alias = schema_editor.connection.alias
    for d in Decklist.objects.using(db_alias).all():
        parsed = DecklistParser.deck.parse(d.content).unwrap()
        d.mainboard = "\n".join(f"{l.qty} {l.name}" for l in parsed.mainboard)
        d.sideboard = "\n".join(f"{l.qty} {l.name}" for l in parsed.sideboard)
        d.save()


class Migration(migrations.Migration):

    dependencies = [
        ("decklists", "0005_collection_staff_key"),
    ]

    operations = [
        migrations.AddField(
            model_name="decklist",
            name="content",
            field=models.TextField(
                default="",
                help_text="Content of the deck, one entry per line, 4 Brainstorm.",
                validators=[decklists.models.validate_decklist_format],
            ),
            preserve_default=False,
        ),
        migrations.RunPython(merge_content, unmerge_content),
        migrations.AlterField(
            model_name="decklist",
            name="mainboard",
            field=models.TextField(default=""),
        ),
        migrations.RemoveField(
            model_name="decklist",
            name="mainboard",
        ),
        migrations.AlterField(
            model_name="decklist",
            name="sideboard",
            field=models.TextField(default=""),
        ),
        migrations.RemoveField(
            model_name="decklist",
            name="sideboard",
        ),
    ]
