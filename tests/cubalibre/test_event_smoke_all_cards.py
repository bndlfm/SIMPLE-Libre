import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv
from app.environments.cubalibre.envs.events import resolve_event
from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA


class TestEventSmokeAllCards(unittest.TestCase):
    def test_all_events_do_not_crash(self):
        env = CubaLibreEnv(verbose=False, manual=False)
        env.reset(seed=5)

        # Keep this test lightweight: just ensure resolve_event doesn't raise.
        env.current_player_num = 0
        env.players[0].eligible = True

        for card_id, data in EVENT_DECK_DATA.items():
            env.current_card = Card(card_id, data["name"], data["order"], data.get("unshaded", ""), data.get("shaded", ""))
            # unshaded
            try:
                resolve_event(env, card_id, play_shaded=False)
            except Exception as e:
                raise AssertionError(f"Event {card_id} unshaded crashed: {e}") from e

            # shaded only if text exists
            if (data.get("shaded") or "").strip():
                try:
                    resolve_event(env, card_id, play_shaded=True)
                except Exception as e:
                    raise AssertionError(f"Event {card_id} shaded crashed: {e}") from e


if __name__ == "__main__":
    unittest.main()
