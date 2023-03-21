from championship.models import Event, EventPlayerResult

FEE_PER_PLAYER = {
    Event.Category.REGULAR: 0,
    Event.Category.REGIONAL: 2,
    Event.Category.PREMIER: 3,
}

TOP8_FEE = {
    Event.Category.REGIONAL: 15,
    Event.Category.PREMIER: 75,
}


def fee_for_event(event: Event) -> int:
    results = EventPlayerResult.objects.filter(event=event)
    has_top8 = results.filter(single_elimination_result__gt=0).count() > 0

    fee = results.count() * FEE_PER_PLAYER[event.category]

    if has_top8:
        fee += TOP8_FEE[event.category]

    return fee
