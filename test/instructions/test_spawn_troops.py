import unittest

from gd.excepts import IssuerDoesNotOwnTerritory, SpawnNotInHeadquarter
from gd.mechanics import SpawnTroops
from gd.world import Headquarter
from test.case import TestCase


class SpawnTroopsTest(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.player, self.other_player = self.generate_players(2)
        self.territory, self.other_territory = self.generate_territories(2, owners=[self.player, self.player])

    def test_spawn_troops_at_hq(self):
        Headquarter(territory=self.territory)
        SpawnTroops(issuer=self.player, territory=self.territory).assert_is_valid()

    def test_spawn_troops_invalid_in_other_player_territory(self):
        Headquarter(territory=self.territory)

        with self.assertRaises(IssuerDoesNotOwnTerritory):
            SpawnTroops(issuer=self.other_player, territory=self.territory).assert_is_valid()

    def test_spawn_troops_invalid_if_not_in_hq_while_player_has_a_hq(self):
        Headquarter(territory=self.other_territory)
        with self.assertRaises(SpawnNotInHeadquarter):
            SpawnTroops(issuer=self.player, territory=self.territory).assert_is_valid()

    def test_spawn_troops_valid_anywhere_if_player_has_no_hq(self):
        SpawnTroops(issuer=self.player, territory=self.territory).assert_is_valid()

    # TODO: add assertions that total troops spawned over multiple instructions is less than the max allowed
    # TODO: add assertions that if the issuer has no HQ, spawning may be done in only one territory per turn


if __name__ == "__main__":
    unittest.main()
