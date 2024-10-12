from datetime import datetime
from bitarray import bitarray
from typing import Generator, List, Any
from bitarray.util import zeros, ones
# from itertools import islice
from timeit import timeit, Timer


def next_cards_iterative(images: int, unused: list, card=None) -> list:
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
            # THIS IS SO UN PERFORMANT. figure out how to do it better lmao

            available = []

            for n in unused[card[-1]]:
                if n <= max_image:
                    if all(n in unused[i] for i in card):
                        available.append(n)

            for n in available:
                # print("    {" + "-" * len(card) + " " * (images - len(card)) + "}")
                yield from next_cards_iterative(images, unused, card + [n])
        else:
            # Final level
            yield card

    return  # No more possible cards


def initialize_unused(deck):
    max_n = deck[len(deck[0]) - 1][-1]  # Last digit of the last 0-card
    unused = [[]]
    # Only iterate through 0-cards
    for card in deck[: len(deck[0])]:
        for _ in card[1:]:
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


def build_deck_iterqueue(images: int) -> list:
    """Builds deck using a queue of iterators."""
    deck = []
    max_deck_size = (images - 1) * images + 1

    # Initialize 0-cards
    n = 0
    while len(deck) < images:
        card = [0]
        while len(card) < images:
            n += 1
            card.append(n)
        deck.append(card)

    unused = initialize_unused(deck)

    queue = [next_cards_iterative(images, unused)]

    while queue:
        # print(f"Queue length {len(queue)}, deck length {len(deck)}")
        try:
            card = next(queue[-1])
        except StopIteration:
            add_card(deck.pop(), unused)
            queue.pop(-1)
            continue

        deck.append(card)
        remove_card(card, unused)

        if len(deck) < max_deck_size:
            queue.append(next_cards_iterative(images, unused))
        else:
            return deck

    # Catch exceptions for a 0-deck
    if len(deck) == max_deck_size:
        return deck


def card_generator(image_count: int, mask: int) -> int:
    # there's room here for optimization, for sure
    card = 1
    while card.bit_length() <= mask.bit_length():
        if bin(card).count("1") == image_count:
            if not (~mask & card):
                yield card
        card += 1



def build_deck_bitmasks(images: int) -> list[int]:
    """Build deck using an array of bitarrays, and bitmasks."""
    deck_size = (images - 1) * images + 1  # also the size each card needs to be
    deck_masks = []
    deck = [0 for _ in range(deck_size)] # the number of images for each card
    usages_of_image = [0 for _ in range(deck_size)]

    card_generators = []

    mask = 0

    # generate the first card
    deck[0] = sum(1 << i for i in range(images))
    completed_cards = 1

    while completed_cards < deck_size:
        # generate another card
        first_available_number = 0
        while usages_of_image[first_available_number] > images:
            first_available_number += 1
        deck[completed_cards] += 1 << first_available_number

        mask = 0
        for card in deck[:completed_cards]:
            if card & deck[completed_cards + 1]:
                mask |= card

    return deck

def build_deck_bitarrays(images: int) -> list[bitarray]:
    size = (images - 1) * images + 1  # size of the deck, and size of each card

    deck = [bitarray(size) for _ in range(size)]
    c = 0  # index of current card
    count_of_usages: list[int] = [0 for _ in range(size)]
    mask_usages = ones(size)

    while c < size:
        masks: list[bitarray] = []

        # mask all bits that have already been used the max amount of times
        # (only need to recalculate if the card changes)
        masks.append(mask_usages)

        if deck[c].count(1):  # these masks can be skipped if current card is blank
            # only include bits to the right of the rightmost set bit in current card
            mask_rightmost = zeros(size)
            mask_rightmost[deck[c].find(1, right=True) + 1:] = 1
            masks.append(mask_rightmost)

            # mask off all bits that have already been used size times
            mask_interference = ones(size)
            for card in deck[:c]:
                if (card & deck[c]).any():
                    mask_interference &= ~card
            masks.append(mask_interference)

        mask = ones(size)
        for m in masks:
            mask &= m
        assert mask.any(), "Mask was completely empty; backtracking is necessary"
        next_bit = mask.find(1)
        deck[c][next_bit] = 1
        count_of_usages[next_bit] += 1

        # check to see if card is done
        if deck[c].count() == images:
            c += 1
            mask_usages = bitarray((value != images for value in count_of_usages))


    return deck

def card_generator_bitarrays(images: int, deck: list[bitarray]) -> Generator[bitarray, None, None]:
    deck_size = (images - 1) * images + 1
    card = zeros(deck_size)

    mask = ones(deck_size)  # ones where bits can be placed

    while card.count() < images:

        next_bit = zeros(deck_size)
        next_bit[card.find(1, right=True) + 1] = 1
        pass


def time1():
    for i in range(2, 50):
        try:
            deck = [card.search(1) for card in build_deck_bitarrays(i)]
            print(f"{i}-deck succeeded")
            deck2 = build_deck_iterqueue(i)
            print("Identical to iterqueue" if deck == deck2 else "Different from iterqueue")
        except AssertionError:
            print(f"{i}-deck failed", end="\r")

    # Decks under 100 that work without backtracking:
    #

def time2():
    for i in range(2, 50):
        try:
            deck = [card.search(1) for card in build_deck_bitarrays(i)]
            print(f"{i}-deck succeeded")
            deck2 = build_deck_iterqueue(i)
            print("Identical to iterqueue" if deck == deck2 else "Different from iterqueue")
        except AssertionError:
            print(f"{i}-deck failed")

    # Decks under 100 that work without backtracking:
    #


def main():
    a = Timer("time1()", globals=globals()).repeat(20, 1)
    b = Timer("time2()", globals=globals()).repeat(20, 1)

    print(min(a))
    print(min(b))

if __name__ == "__main__":
    main()