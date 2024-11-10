from spotit import build_deck_v4, check_deck


def test_good_decks():
    known_good_decks = [2, 3, 4, 5, 9, 17]
    result_decks = []
    result_checks = []
    for i in known_good_decks:
        deck = build_deck_v4(known_good_decks)
        result_decks.append(deck)
        result_checks.append(check_deck(deck))
    assert all(result_checks)
