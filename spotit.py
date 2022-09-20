from itertools import islice
from datetime import datetime


def next_cards_iterative(images, unused, card=None):
    # Initialize
    if card is None:
        card = []
        for i, n in enumerate(unused):
            if len(n) > 0:
                card = [i]
                break

    if len(card) > 0:
        if len(card) < images:
            # Further levels required
            max_image = (images - 1) * (len(card) + 1)
            available = (
                n
                for n in unused[card[-1]]  # for debugging
                if n <= max_image
                if all(n in unused[i] for i in card)
            )

            for n in available:
                # print("    {" + "-" * len(card) + " " * (images - len(card)) + "}")
                yield from next_cards_iterative(images, unused, card + [n])
        else:
            # Final level
            yield card

    return "You've reached the end of the valid cards, buckaroo"


def initialize_unused(deck):
    max_n = deck[len(deck[0]) - 1][-1]  # Last digit of the last 0-card
    unused = [[]]
    # Only iterate through 0-cards
    for card in deck[: len(deck[0])]:
        for n in card[1:]:
            unused.append([i + 1 for i in range(card[-1], max_n)])

    # If deck is longer than just the zeroes:
    for card in deck[len(deck[0]) :]:
        remove_card(card, unused)

    return unused


def remove_card(card, unused):
    for i, n in enumerate(card):
        for n2 in card[i + 1 :]:
            unused[n].remove(n2)

    return unused


def add_card(card, unused):
    for i, n in enumerate(card):
        for n2 in card[i + 1 :]:
            unused[n].append(n2)
        unused[n].sort()

    return unused


def deck_iterator(images_per_card, deck=None, unused=None, verbose=0, attempts=0):

    if deck is None:
        deck = []

        # Initialize 0-cards
        n = 0
        while len(deck) < images_per_card:
            card = [0]
            while len(card) < images_per_card:
                n += 1
                card.append(n)
            deck.append(card)
            if verbose == 1:
                print(card)

        unused = initialize_unused(deck)

    possible_cards = next_cards_iterative(images_per_card, unused)

    max_deck_size = (images_per_card - 1) * images_per_card + 1
    print(
        datetime.now().strftime("%H:%M:%S"),
        f"{images_per_card}-deck: {len(deck)} of {max_deck_size}",
    )

    i = 0

    for card in possible_cards:
        # if not directly_follows(deck[-1], card):
        #     continue  # TODO: probably a faster way to do this
        i += 1
        unused = remove_card(card, unused)
        yield from deck_iterator(
            images_per_card,
            deck=deck + [card],
            unused=unused,
            verbose=verbose,
            attempts=attempts,
        )

        unused = add_card(card, unused)

    if i == 0:
        yield deck


def build_deck(images, limit=1000):
    max_deck_size = (images - 1) * images + 1

    for attempt, deck in enumerate(deck_iterator(images)):

        # print("[" + "=" * len(deck) + " " * (max_deck_size - len(deck)) + "]", attempt)

        if len(deck) == max_deck_size:
            print("{images}-deck found in {attempt} iterations")
            return deck

        if attempt >= limit:
            print(f"{images}-deck not found in under {attempt} iterations")
            break


def check_deck(deck):
    images = len(deck[0])

    print("Checking each card length... ", end="", flush=True)
    for c in deck:
        assert len(c) == images
    print("Done")

    print("Checking total usages of each number... ", end="", flush=True)
    usages = []
    for c in deck:
        for i in c:
            while len(usages) < i + 1:
                usages.append(0)
            usages[i] += 1
    assert all(u == images for u in usages)
    print("Done")


def build_deck_loop(images):
    pass


for i in range(30):
    images = i + 1
    max_deck_size = (images - 1) * images + 1
    if len(next(deck_iterator(images))) == max_deck_size:
        print(f"{images}-deck found", flush=True)
    else:
        print(f"{images}-deck not found", flush=True)
