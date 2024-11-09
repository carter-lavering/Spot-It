from datetime import datetime

from bitarray import bitarray
from bitarray.util import ba2int, ones, zeros


def build_deck_bitarrays(
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
                    # print(f"{deck[c]} is bad, seen before")
                    pass
                else:
                    print(f"{deck[c]} is bad, new")
                    known_bad_cards.add(ba2int(deck[c]))
            else:
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
