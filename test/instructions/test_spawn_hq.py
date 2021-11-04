import unittest

from excepts import IssuerAlreadyPresentInWorld, AdjacentTerritoryNotEmpty, TerritoryNotNeutral
from test.case import TestCase
from world import CreateHeadquarter


class SpawnHeadquarterTest(TestCase):

    def test_spawn_headquarter_is_possible(self):
        player, = self.generate_players(1)
        territory, = self.generate_territories(1)
        CreateHeadquarter(issuer=player, territory=territory, world=self.world).assert_is_valid()

    def test_spawn_headquarter_is_impossible_if_player_already_has_territories(self):
        player, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[player])

        with self.assertRaises(IssuerAlreadyPresentInWorld):
            CreateHeadquarter(issuer=player, territory=t2, world=self.world).assert_is_valid()

    def test_spawn_headquarter_is_impossible_if_adjacent_land_is_not_empty(self):
        p1, p2 = self.generate_players()
        t1, t2 = self.generate_territories(owners=[p1])
        t1.link(t2)
        self.generate_troops({t1: 1})

        with (self.assertRaises(AdjacentTerritoryNotEmpty)):
            CreateHeadquarter(issuer=p2, territory=t2, world=self.world).assert_is_valid()

    def test_spawn_headquarter_is_impossible_if_land_is_not_neutral(self):
        p1, p2 = self.generate_players()
        t1, t2 = self.generate_territories(owners=[p1])

        with (self.assertRaises(TerritoryNotNeutral)):
            CreateHeadquarter(issuer=p2, territory=t1, world=self.world).assert_is_valid()

        CreateHeadquarter(issuer=p2, territory=t2, world=self.world).assert_is_valid()


if __name__ == "__main__":
    unittest.main()
