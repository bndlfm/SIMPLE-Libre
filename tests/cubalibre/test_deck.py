import unittest

from app.environments.cubalibre.envs.classes import Deck


class TestDeck(unittest.TestCase):
    def test_deck_size_and_propaganda_count(self):
        d = Deck()
        # 48 events + 4 propaganda
        self.assertEqual(len(d.cards), 52)

        propaganda = sum(1 for c in d.cards if getattr(c, "is_propaganda", False))
        events = sum(1 for c in d.cards if not getattr(c, "is_propaganda", False))
        self.assertEqual(propaganda, 4)
        self.assertEqual(events, 48)


if __name__ == "__main__":
    unittest.main()
