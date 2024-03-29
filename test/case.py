import unittest
from typing import Any

from gd.logger import logger
from test import generate_name
from gd.world import Territory, Troop, Player, World, Construct, Boundary


class TestCase(unittest.TestCase):
    world: World

    def setUp(self) -> None:
        self.world = World()
        logger.debug(f"Running test: [b][yellow]{self._testMethodName}[/yellow][/b]")
        logger.indents += 1

    def tearDown(self) -> None:
        logger.indents -= 1
        logger.debug(f"Finished test: [b][yellow]{self._testMethodName}[/yellow][/b]")

    def skipTest(self, reason: Any) -> None:
        logger.warning(f"[red]Skipped test[/red] ([i]{reason}[/i])")
        super().skipTest(reason)

    def assertTerritoryHasTroops(self, territory: Territory, num_troops: int) -> None:
        self.assertEqual(num_troops, len(territory.all(Troop)))

    def assertTerritoryOwner(self, territory: Territory, player: Player) -> None:
        self.assertEqual(player, territory.owner)

    def assertTerritoryNeutral(self, territory: Territory) -> None:
        self.assertIsNone(territory.owner)

    def assertTerritoryHasConstruct(self, territory: Territory, construct_type: type[Construct]):
        for construct in territory.constructs:
            if isinstance(construct, construct_type):
                return

        raise AssertionError(f"No construct of type {construct_type} found in territory")

    def generate_territories(self, amount: int = 2, owners: list[Player] = None, complete_graph=True) -> list[Territory]:
        if owners is None:
            owners = [None for _ in range(amount)]

        if len(owners) < amount:
            # Pad the owner list with Nones if necessary
            owners += [None for _ in range(amount - len(owners))]

        # Register the territories into the world.
        for territory in (territories := [Territory(owner=owner, world=self.world) for owner in owners]):
            self.world.territories[territory.id] = territory

        # Link all territories together
        if complete_graph:
            for territory_1 in territories:
                for territory_2 in territories:
                    self.world.boundaries.add(Boundary(territories=(territory_1, territory_2)))

        return territories

    def generate_players(self, amount: int = 2) -> list[Player]:
        return [Player(name=generate_name(), world=self.world) for _ in range(amount)]

    @staticmethod
    def generate_troops(troops_by_territory: dict[Territory, int]) -> None:
        for territory, num_troops in troops_by_territory.items():
            for i in range(num_troops):
                Troop(territory=territory)
