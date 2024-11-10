from spotit import build_deck_v4, check_deck
from bitarray import bitarray


# def test_good_decks(benchmark):
#     known_good_decks = [2, 3, 4, 5, 9, 17]
#     result_decks = []
#     result_checks = []
#     for i in known_good_decks:
#         deck = benchmark(build_deck_v4, i)
#         result_decks.append(deck)
#         result_checks.append(check_deck(deck))
#     for d, c in zip(result_decks, result_checks):
#         assert c


def test_2(benchmark):
    deck = benchmark(build_deck_v4, 2)


def test_3(benchmark):
    deck = benchmark(build_deck_v4, 3)


def test_4(benchmark):
    deck = benchmark(build_deck_v4, 4)


def test_5(benchmark):
    deck = benchmark(build_deck_v4, 5)


def test_6(benchmark):
    deck = benchmark(build_deck_v4, 6)


def test_9(benchmark):
    deck = benchmark(build_deck_v4, 9)


def test_17(benchmark):
    deck = benchmark(build_deck_v4, 17)


# def test_bad_decks():
#     known_bad_decks = [6, 7, 8, 10, 11]
#     result_decks = []
#     result_checks = []
#     for i in known_bad_decks:
#         deck = build_deck_v4(i)
#         result_decks.append(deck)
#         result_checks.append(check_deck(deck))
#     for d, c in zip(result_decks, result_checks):
#         assert not c
