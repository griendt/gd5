import unittest

from gd.excepts import IssuerDoesNotOwnTerritory, SpawnNotInHeadquarter
from gd.mechanics import SpawnTroops, MovementChain, Turn
from gd.world import Headquarter
from test.case import TestCase


class SpawnTroopsTest(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.player, self.other_player = self.generate_players(2)
        self.territories = self.generate_territories(3, owners=[self.player, self.player])

    def test_movement_chain(self):
        self.generate_troops({self.territories[0]: 10})

        ids = [territory.id for territory in self.territories]
        chain = MovementChain(issuer=self.player, world=self.world, origin_num_destinations=[
            (ids[0], 10, ids[1]),
            (ids[1], 8, ids[2]),
        ])

        chain.assert_is_valid()
        Turn([chain]).execute()

        self.assertTerritoryHasTroops(self.territories[0], 0)
        self.assertTerritoryHasTroops(self.territories[1], 2)
        self.assertTerritoryHasTroops(self.territories[2], 8)


if __name__ == "__main__":
    unittest.main()
