from datetime import datetime
from typing import Generator
from timeout import timeout

from bitarray import bitarray
from bitarray.util import ba2int, ones, zeros, any_and


def next_cards_iterative(
    images: int, unused: list[list[int]], card=None
) -> Generator[list[int]]:
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


def initialize_unused(deck) -> list[list[int]]:
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


def check_deck(deck) -> bool:
    if not len(deck):
        print("Deck is empty")
        return False

    images = len(deck[0])

    length_check = True
    print("Checking each card length... ", end="", flush=True)
    for c in deck:
        if len(c) != images:
            length_check = False
    print("Passed" if length_check else "Failed")

    usages_check = True
    print("Checking total usages of each number... ", end="", flush=True)
    usages = []
    for c in deck:
        for i in c:
            while len(usages) < i + 1:
                usages.append(0)
            usages[i] += 1
    max_usages_check = all(u <= images for u in usages)
    exact_usages_check = all(u == images for u in usages)
    print(
        "Passed perfectly"
        if exact_usages_check
        else ("Passed (incomplete deck)" if max_usages_check else "Failed")
    )

    return length_check and usages_check


def build_deck_iterqueue(images: int):
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


def card_generator(image_count: int, mask: int) -> Generator[int]:
    # there's room here for optimization, for sure
    card = 1
    while card.bit_length() <= mask.bit_length():
        if bin(card).count("1") == image_count:
            if not (~mask & card):
                yield card
        card += 1


def build_deck_clear_bad_cards(
    images: int, *, early_stop_size: int = None
) -> list[list[int]]:
    time_start = datetime.now()
    card_size = (images - 1) * images + 1  # size of each card (number of unique images)
    if early_stop_size is None:
        deck_size = card_size
    else:
        deck_size = early_stop_size

    deck = [bitarray(card_size) for _ in range(deck_size)]
    c = 0  # index of current card
    count_of_usages: list[int] = [0 for _ in range(card_size)]
    mask_usages = ones(card_size)
    # masks: list[bitarray] = []
    mask = ones(card_size)
    has_backtracked = False
    lowest_card_backtracked = card_size
    max_card_reached = 0
    cleared_card_count = [0] * deck_size
    known_bad_cards = set()

    while c < deck_size:
        # start with all possibilities

        # card is blank
        if not deck[c].any():
            pass  # no additional parsing required

        # card has some bits, but not all
        elif deck[c].count(1) < images:
            # mask off all bits to the left of rightmost bit (inclusive)
            rightmost_bit = deck[c].find(1, right=True) + 1  # +1 because inclusive
            mask &= zeros(rightmost_bit) + ones(card_size - rightmost_bit)

            # only allow bits that haven't appeared in any of the same cards as this card's other bits
            for mask_card in deck[:c]:
                if (mask_card & deck[c]).any():  # if mask_card and c share any bits
                    mask &= ~mask_card  # get rid of the rest of the bits in mask_card

        # card has the maximum number of bits
        elif deck[c].count(1) == images:
            if c < deck_size - 1:
                # finished card isn't the last card
                # print(f"Card {c} filled at {datetime.now() - time_start}")
                c += 1
                if c > max_card_reached:
                    max_card_reached = c
                    # print(f"Card {c} reached after {datetime.now() - time_start}")
                continue
            else:
                break

        else:
            print("Something has gone terribly wrong")

        # now that we've filtered, let's check to see if we have any possible bits
        if mask.any():
            next_bit = mask.find(1)
            deck[c][next_bit] = 1
            count_of_usages[next_bit] += 1
            if count_of_usages[next_bit] == images:
                mask_usages[next_bit] = 0
            mask = mask_usages.copy()
        else:  # need to backtrack
            if deck[c].any():
                card_as_int = ba2int(deck[c])
                if card_as_int in known_bad_cards:
                    print(f"{deck[c]} is bad, seen before. clearing card...")
                    for i in deck[c].search(1):
                        count_of_usages[i] -= 1
                    deck[c][:] = 0
                else:
                    print(f"{deck[c]} is bad, new")
                    known_bad_cards.add(ba2int(deck[c]))

            if not deck[c].any():
                if c == 0:  # backtracked all the way back to the beginning
                    return []
                # current card is empty, go back one card
                cleared_card_count[c] += 1
                lowest_card_backtracked = min(c, lowest_card_backtracked)
                c -= 1
                # print(
                #     lowest_card_backtracked,
                #     cleared_card_count[lowest_card_backtracked:],
                #     end="\r",
                # )

            mask = mask_usages.copy()
            rightmost_bit = deck[c].find(1, right=True)
            deck[c][rightmost_bit] = 0
            count_of_usages[rightmost_bit] -= 1
            if count_of_usages[rightmost_bit] == images - 1:
                mask_usages[rightmost_bit] = 1
            mask[: rightmost_bit + 1] = 0

    print()
    return [c.search(1) for c in deck]


def build_deck_v1(
    images: int, *, early_stop_size: int = None
) -> list[list[int]] | None:
    time_start = datetime.now()
    card_size = (images - 1) * images + 1  # size of each card (number of unique images)

    if early_stop_size is None:
        deck_size = card_size
    else:
        deck_size = min(card_size, early_stop_size)

    deck = [bitarray(card_size) for _ in range(deck_size)]
    c = 0  # index of current card
    count_of_usages: list[int] = [0 for _ in range(card_size)]
    mask_usages = ones(card_size)
    mask = ones(card_size)
    lowest_card_backtracked = card_size
    highest_card_backtracked = 0
    max_card_reached = 0
    cleared_card_count = [0] * deck_size
    known_bad_cards = set()

    while c < deck_size:
        # step 1: mask off unusable values
        if not deck[c].any():
            # we're on a blank card, reset mask
            mask = mask_usages.copy()

        elif deck[c].count(1) < images:
            # mask off all bits to the left of rightmost bit (inclusive)
            rightmost_bit = deck[c].find(1, right=True) + 1  # +1 because inclusive
            mask &= zeros(rightmost_bit) + ones(card_size - rightmost_bit)

            # only allow bits that haven't appeared in any of the same cards as this card's other bits
            for mask_card in deck[:c]:
                if (mask_card & deck[c]).any():  # if mask_card and c share any bits
                    mask &= ~mask_card  # get rid of the rest of the bits in mask_card

        elif deck[c].count(1) == images:
            if c < deck_size - 1:
                # finished card isn't the last card
                # print(f"({images}) Card {c} filled: {datetime.now() - time_start}")
                c += 1
                if c > max_card_reached:
                    max_card_reached = c
                    print(
                        f"({images}) Card {c} of {deck_size} reached: {datetime.now() - time_start}"
                    )
                continue
            else:
                break

        else:
            print("Something has gone terribly wrong")

        # now that we've filtered, let's check to see if we have any possible bits
        if mask.count() + deck[c].count() >= images:
            next_bits_generator = mask.search(1)
        else:
            next_bits_generator = []
        for next_bit in next_bits_generator:
            # try a bit from the mask
            deck[c][next_bit] = 1
            if ba2int(deck[c]) not in known_bad_cards:
                # card is good (potentially)
                count_of_usages[next_bit] += 1
                if count_of_usages[next_bit] == images:
                    mask_usages[next_bit] = 0
                break
            else:
                # already seen this exact card before and needed to backtrack
                # we reset the bit and move on to the next generated one
                deck[c][next_bit] = 0

        else:  # no good bits found, need to backtrack
            # everything in this block only triggers if there are no new good bits
            if deck[c].any():
                card_as_int = ba2int(deck[c])
                if card_as_int not in known_bad_cards:
                    print(f"Card {c} {deck[c]} is bad, new")
                    known_bad_cards.add(ba2int(deck[c]))

                    # for i in deck[c].search(1):
                    #     count_of_usages[i] -= 1
                    # deck[c][:] = 0
                else:
                    print(f"Card {c} {deck[c]} is bad, seen before")
                    pass

            if not deck[c].any():
                if c > images * 2:
                    # we haven't backtracked too far
                    cleared_card_count[c] += 1
                    print(
                        lowest_card_backtracked,
                        cleared_card_count[
                            lowest_card_backtracked:highest_card_backtracked
                        ],
                        end="\r",
                    )
                    lowest_card_backtracked = min(c, lowest_card_backtracked)
                    highest_card_backtracked = max(c, highest_card_backtracked)
                    c -= 1
                else:
                    # we've backtracked to the first two levels of the deck. it's ogre
                    deck = None
                    break
                # current card is empty

            mask = mask_usages.copy()
            rightmost_bit = deck[c].find(1, right=True)
            deck[c][rightmost_bit] = 0
            count_of_usages[rightmost_bit] -= 1
            if count_of_usages[rightmost_bit] == images - 1:
                mask_usages[rightmost_bit] = 1
            mask[: rightmost_bit + 1] = 0

        # end of while loop
        pass

    print()
    print(f"Accumulated {len(known_bad_cards)} known bad cards")
    # print(
    #     "Card backtrack counts: {}".format(
    #         [(i, count) for i, count in enumerate(cleared_card_count) if count > 0]
    #     )
    # )
    if deck:
        return [c.search(1) for c in deck]
    else:
        return None


def build_deck_v2(
    images: int, *, early_stop_size: int = None
) -> list[list[int]] | None:
    time_start = datetime.now()
    card_size = (images - 1) * images + 1  # size of each card (number of unique images)

    if early_stop_size is None:
        deck_size = card_size
    else:
        deck_size = min(card_size, early_stop_size)

    deck = [bitarray(card_size) for _ in range(deck_size)]
    c = 0  # index of current card
    count_of_usages: list[int] = [0 for _ in range(card_size)]
    mask_usages = ones(card_size)
    mask = ones(card_size)
    lowest_card_backtracked = card_size
    highest_card_backtracked = 0
    max_card_reached = 0
    cleared_card_count = [0] * deck_size
    known_bad_cards = set()

    while c < deck_size:
        # step 1: mask off unusable values

        if not deck[c].any():
            # we're on a blank card, reset mask
            mask = mask_usages.copy()

        elif deck[c].count(1) < images:
            # mask off all bits to the left of rightmost bit (inclusive)
            rightmost_bit = deck[c].find(1, right=True) + 1  # +1 because inclusive
            mask &= zeros(rightmost_bit) + ones(card_size - rightmost_bit)

            # only allow bits that haven't appeared in any of the same cards as this card's other bits
            for mask_card in deck[:c]:
                if (mask_card & deck[c]).any():  # if mask_card and c share any bits
                    mask &= ~mask_card  # get rid of the rest of the bits in mask_card

        elif deck[c].count(1) == images:
            if c < deck_size - 1:
                # finished card isn't the last card
                # print(f"({images}) Card {c} filled: {datetime.now() - time_start}")
                c += 1
                if c > max_card_reached:
                    max_card_reached = c
                    print(
                        f"({images}) Card {c} of {deck_size} reached: {datetime.now() - time_start}"
                    )
                continue
            else:
                break

        else:
            print("Something has gone terribly wrong")

        # now that we've filtered, let's check to see if we have any possible bits

        if mask.count() + deck[c].count() >= images:
            next_bits_generator = mask.search(1)
        else:
            next_bits_generator = []

        # next_bits_generator = mask.itersearch(1)

        for next_bit in next_bits_generator:
            # try a bit from the mask
            deck[c][next_bit] = 1
            if ba2int(deck[c]) not in known_bad_cards:
                # card is good (potentially)
                count_of_usages[next_bit] += 1
                if count_of_usages[next_bit] == images:
                    mask_usages[next_bit] = 0
                break
            else:
                # already seen this exact card before and needed to backtrack
                # we reset the bit and move on to the next generated one
                deck[c][next_bit] = 0

        else:  # no good bits found, need to backtrack
            # everything in this block only triggers if there are no new good bits
            if deck[c].any():
                card_as_int = ba2int(deck[c])
                if card_as_int not in known_bad_cards:
                    print(f"Card {c} {deck[c]} is bad, new")
                    known_bad_cards.add(ba2int(deck[c]))
                else:
                    print(f"Card {c} {deck[c]} is bad, seen before")
                    pass

            if not deck[c].any():
                if c > images * 2:
                    # we haven't backtracked too far
                    cleared_card_count[c] += 1
                    print(
                        lowest_card_backtracked,
                        cleared_card_count[
                            lowest_card_backtracked:highest_card_backtracked
                        ],
                        end="\r",
                    )
                    lowest_card_backtracked = min(c, lowest_card_backtracked)
                    highest_card_backtracked = max(c, highest_card_backtracked)
                    c -= 1
                else:
                    # we've backtracked to the first two levels of the deck. it's ogre
                    deck = None
                    break
                # current card is empty

            mask = mask_usages.copy()
            rightmost_bit = deck[c].find(1, right=True)
            deck[c][rightmost_bit] = 0
            count_of_usages[rightmost_bit] -= 1
            if count_of_usages[rightmost_bit] == images - 1:
                mask_usages[rightmost_bit] = 1
            mask[: rightmost_bit + 1] = 0

        # end of while loop
        pass

    print()
    print(f"Accumulated {len(known_bad_cards)} known bad cards")
    # print(
    #     "Card backtrack counts: {}".format(
    #         [(i, count) for i, count in enumerate(cleared_card_count) if count > 0]
    #     )
    # )
    if deck:
        return [c.search(1) for c in deck]
    else:
        return None


def build_deck_v3(
    images: int, *, early_stop_size: int = None, backtrack: bool = True
) -> list[list[int]] | None:
    time_start = datetime.now()
    card_size = (images - 1) * images + 1  # size of each card (number of unique images)

    if early_stop_size is None:
        deck_size = card_size
    else:
        deck_size = min(card_size, early_stop_size)

    deck = [bitarray(card_size) for _ in range(deck_size)]
    c = 0  # index of current card
    count_of_usages: list[int] = [0 for _ in range(card_size)]
    mask_usages = ones(card_size)
    mask = ones(card_size)
    lowest_card_backtracked = card_size
    highest_card_backtracked = 0
    max_card_reached = 0
    cleared_card_count = [0] * deck_size
    known_bad_cards = set()
    cache_hits = 0

    while c < deck_size:
        # step 1: mask off unusable values

        if not deck[c].any():
            # we're on a blank card, reset mask
            mask = mask_usages.copy()

        elif deck[c].count(1) < images:
            # mask off all bits to the left of rightmost bit (inclusive)
            rightmost_bit = deck[c].find(1, right=True) + 1  # +1 because inclusive
            mask &= zeros(rightmost_bit) + ones(card_size - rightmost_bit)

            # only allow bits that haven't appeared in any of the same cards as this card's other bits
            for mask_card in deck[:c]:
                if any_and(mask_card, deck[c]):  # if mask_card and c share any bits
                    mask &= ~mask_card  # get rid of the rest of the bits in mask_card

        elif deck[c].count(1) == images:
            if c < deck_size - 1:
                # finished card isn't the last card
                # print(f"({images}) Card {c} filled: {datetime.now() - time_start}")
                c += 1
                if c > max_card_reached:
                    max_card_reached = c
                    print(
                        f"({images}) Card {c} of {deck_size} reached: {datetime.now() - time_start}"
                    )
                continue
            else:
                break

        else:
            print("Something has gone terribly wrong")

        # now that we've filtered, let's check to see if we have any possible bits
        if c >= images:
            mask_nth_bit = deck[deck[c].count()]
        else:
            mask_nth_bit = ones(card_size)

        if mask.count() + deck[c].count() >= images:
            next_bits_generator = (mask & mask_nth_bit).search(1)
        else:
            next_bits_generator = []

        # next_bits_generator = mask.itersearch(1)

        for next_bit in next_bits_generator:
            # try a bit from the mask
            deck[c][next_bit] = 1
            if ba2int(deck[c]) not in known_bad_cards:
                # card is good (potentially)
                count_of_usages[next_bit] += 1
                if count_of_usages[next_bit] == images:
                    mask_usages[next_bit] = 0
                break
            else:
                # already seen this exact card before and needed to backtrack
                # we reset the bit and move on to the next generated one
                cache_hits += 1
                deck[c][next_bit] = 0

        else:  # no good bits found, need to backtrack
            # everything in this block only triggers if there are no new good bits
            if deck[c].any():
                card_as_int = ba2int(deck[c])
                if card_as_int not in known_bad_cards:
                    # print(f"Card {c} {deck[c]} is bad, new")
                    known_bad_cards.add(ba2int(deck[c]))
                else:
                    print(f"Card {c} {deck[c]} is bad, seen before")
                    cache_hits += 1
                    pass

            if not deck[c].any():
                if c > images * 2:
                    # we haven't backtracked too far
                    cleared_card_count[c] += 1
                    print(
                        lowest_card_backtracked,
                        cleared_card_count[
                            lowest_card_backtracked:highest_card_backtracked
                        ],
                        end="\r",
                    )
                    lowest_card_backtracked = min(c, lowest_card_backtracked)
                    highest_card_backtracked = max(c, highest_card_backtracked)
                    c -= 1
                else:
                    # we've backtracked to the first two levels of the deck. it's ogre
                    deck = None
                    break
                # current card is empty

            mask = mask_usages.copy()
            rightmost_bit = deck[c].find(1, right=True)
            deck[c][rightmost_bit] = 0
            count_of_usages[rightmost_bit] -= 1
            if count_of_usages[rightmost_bit] == images - 1:
                mask_usages[rightmost_bit] = 1
            mask[: rightmost_bit + 1] = 0

        # end of while loop
        pass

    print()
    print(f"{len(known_bad_cards)} known bad cards cached")
    print(f"{cache_hits} known bad cards skipped")
    # print(
    #     "Card backtrack counts: {}".format(
    #         [(i, count) for i, count in enumerate(cleared_card_count) if count > 0]
    #     )
    # )
    if deck:
        return [c.search(1) for c in deck]
    else:
        return None


def build_deck_v4(
    images: int, *, early_stop_size: int = None, backtrack: bool = True
) -> list[list[int]] | None:
    time_start = datetime.now()
    card_size = (images - 1) * images + 1  # size of each card (number of unique images)

    if early_stop_size is None:
        deck_size = card_size
    else:
        deck_size = min(card_size, early_stop_size)

    deck = [bitarray(card_size) for _ in range(deck_size)]
    c = 0  # index of current card
    count_of_usages: list[int] = [0 for _ in range(card_size)]
    mask_usages = ones(card_size)
    mask = ones(card_size)
    lowest_card_backtracked = card_size
    highest_card_backtracked = 0
    max_card_reached = 0
    cleared_card_count = [0] * deck_size
    known_bad_cards = set()
    cache_hits = 0
    collisions_by_images = [bitarray(card_size) for _ in range(card_size)]

    while c < deck_size:
        # step 1: mask off unusable values
        images_on_card = deck[c].count(1)

        if images_on_card == 0:
            # we're on a blank card, reset mask
            mask = mask_usages.copy()

        elif images_on_card < images:
            # mask off all bits to the left of rightmost bit (inclusive)
            rightmost_bit = deck[c].find(1, right=True) + 1  # +1 because inclusive
            mask[0:rightmost_bit] = 0

            # only allow bits that haven't appeared in any of the same cards as this card's other bits

            mask_changed_list = []
            mask_unchanged_list = []
            for i in deck[c].search(1):
                mask_prev = mask.copy()
                mask &= ~collisions_by_images[i]
                if mask != mask_prev:
                    mask_changed_list.append(i)
                else:
                    mask_unchanged_list.append(i)
            print(f"{mask_unchanged_list=}, {mask_changed_list=}")

        elif images_on_card == images:
            if c < deck_size - 1:
                # finished card isn't the last card
                # print(f"({images}) Card {c} filled: {datetime.now() - time_start}")
                for i in deck[c].search(1):
                    collisions_by_images[i] |= deck[c]
                c += 1
                if c > max_card_reached:
                    max_card_reached = c
                    print(
                        f"({images}) Card {c} of {deck_size} reached: {datetime.now() - time_start}"
                    )
                continue
            else:
                break

        else:
            print("Something has gone terribly wrong")

        # now that we've filtered, let's check to see if we have any possible bits
        if c >= images:
            mask_nth_bit = deck[deck[c].count()]
        else:
            mask_nth_bit = ones(card_size)

        if mask.count() + deck[c].count() >= images:
            next_bits_generator = (mask & mask_nth_bit).search(1)
        else:
            next_bits_generator = []

        # next_bits_generator = mask.itersearch(1)

        for next_bit in next_bits_generator:
            # try a bit from the mask
            deck[c][next_bit] = 1
            if ba2int(deck[c]) not in known_bad_cards:
                # card is good (potentially)
                count_of_usages[next_bit] += 1
                if count_of_usages[next_bit] == images:
                    mask_usages[next_bit] = 0
                break
            else:
                # already seen this exact card before and needed to backtrack
                # we reset the bit and move on to the next generated one
                cache_hits += 1
                deck[c][next_bit] = 0

        else:  # no good bits found, need to backtrack
            # everything in this block only triggers if there are no new good bits
            if deck[c].any():
                card_as_int = ba2int(deck[c])
                if card_as_int not in known_bad_cards:
                    # print(f"Card {c} {deck[c]} is bad, new")
                    known_bad_cards.add(ba2int(deck[c]))
                else:
                    # print(f"Card {c} {list(deck[c].search(1))} is bad, seen before")
                    cache_hits += 1
                    pass

            if not deck[c].any():
                if c > images * 2:
                    # we haven't backtracked too far
                    cleared_card_count[c] += 1
                    print(
                        lowest_card_backtracked,
                        cleared_card_count[
                            lowest_card_backtracked:highest_card_backtracked
                        ],
                        end="\r",
                    )
                    lowest_card_backtracked = min(c, lowest_card_backtracked)
                    highest_card_backtracked = max(c, highest_card_backtracked)
                    c -= 1
                    for i in deck[c].search(1):
                        collisions_by_images[i] ^= deck[c]
                else:
                    # we've backtracked to the first two levels of the deck. it's ogre
                    deck = None
                    break
                # current card is empty

            mask = mask_usages.copy()
            rightmost_bit = deck[c].find(1, right=True)
            deck[c][rightmost_bit] = 0
            count_of_usages[rightmost_bit] -= 1
            if count_of_usages[rightmost_bit] == images - 1:
                mask_usages[rightmost_bit] = 1
            mask[: rightmost_bit + 1] = 0

        # end of while loop
        pass

    print()
    print(f"{len(known_bad_cards)} known bad cards cached")
    print(f"{cache_hits} known bad cards skipped")
    # print(
    #     "Card backtrack counts: {}".format(
    #         [(i, count) for i, count in enumerate(cleared_card_count) if count > 0]
    #     )
    # )
    if deck:
        return [list(c.search(1)) for c in deck]
    else:
        return None


def comprehensible(images: int, card: bitarray) -> list[int]:
    result = []
    for i in range(images):
        result.append((card << (images * i)).find(1))
    return result


def main():
    images = [33]
    time_limit = 60  # seconds
    # deck_functions = [build_deck_v1, build_deck_v2, build_deck_v3, build_deck_v4]
    deck_functions = [build_deck_v4]
    result_decks = []
    result_times = []
    try:
        for i in images:
            print(f"Making {i}-deck...")
            result_decks.append([])
            result_times.append([])
            for f in deck_functions:
                try:
                    time_start = datetime.now()
                    # with timeout(time_limit):
                    deck = f(i)
                    time_end = datetime.now()
                    result_decks[-1].append(deck)
                    result_times[-1].append(time_end - time_start)
                except TimeoutError:
                    result_decks[-1].append(None)
                    result_times[-1].append(None)
            result_decks

    except KeyboardInterrupt:
        print("Keyboard interrupted")

    print()
    print("\t" + "\t".join(f.__name__ for f in deck_functions))

    for i, times, decks in zip(images, result_times, result_decks):
        print(f"{i:2}-deck", end="\t")
        print("\t".join(str(t) for t in times), decks[0] != None)


if __name__ == "__main__":
    main()
