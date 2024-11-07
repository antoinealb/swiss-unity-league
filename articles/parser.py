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
from collections.abc import Iterator
from typing import Union

from parsita import ParserContext, eof, failure, lit, opt, reg, rep1, success, until


@dataclasses.dataclass
class CardTag:
    card_name: str


@dataclasses.dataclass
class DecklistTag:
    uid: str


@dataclasses.dataclass
class ImageTag:
    url: str
    alt_text: str = ""


ParsedText = Union[CardTag, str]


def non_null_length(*args):
    if not args or args[0] == "":
        return failure("Should not be null length")
    return success(args[0])


class ArticleTagParser(ParserContext):  # type: ignore
    card = reg(r"[^\[\]\r\n]*") > (lambda s: s.rstrip())
    opening_tag = lit("[[")
    closing_tag = lit("]]")
    protocol = lit("http") | lit("https")
    uuid = reg(r"[0-9a-f\-]+")
    decklist = protocol >> lit("://unityleague.ch/decklists/") >> uuid << opt(lit("/"))
    tag_content = (decklist > DecklistTag) | (card > CardTag)
    tag = opening_tag >> tag_content << closing_tag

    # A markdown-style image link
    image_alt_text = reg(r"[^\]]*")
    image_url = reg(r"[^\)]*")
    image_tag = lit("![") >> image_alt_text << lit("](") & image_url << lit(")") > (
        lambda s: ImageTag(url=s[1], alt_text=s[0])
    )

    text = until(tag | image_tag | eof) >= non_null_length

    article = rep1(tag | image_tag | text)


def extract_tags(text: str) -> Iterator[ParsedText]:
    """Parses a block of text, extracting possible tag candidates.
    >>> list(extract_tags('Foobar'))
    ['Foobar']

    >>> list(extract_tags('[[Ragavan, Nimble Pilferer]] is a monkey.'))
    [CardTag(card_name='Ragavan, Nimble Pilferer'), ' is a monkey.']
    """
    res = ArticleTagParser.article.parse(text)

    for chunk in res.unwrap():
        if not chunk:
            # skip empty strings
            continue

        yield chunk
