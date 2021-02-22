import unittest

from faker import Faker

from excepts import InsufficientUnitsException
from world import World, Territory, LandBiome, Player, Troop, Unit, General, Cavalry


class WorldTest(unittest.TestCase):
    faker = Faker()

    def test_empty_world_initialization(self):
        """A world can be initialized without parameters."""
        world = World()
        self.assertEqual(0, len(world.territories))

    def test_territory_initialization_without_parameters(self):
        """A territory can be initialized without parameters."""
        territory = Territory()
        self.assertIsInstance(territory.id, int)

    def test_territory_id_autoincrement(self):
        """Territories have an id field that should increment automatically
        when new instances are created."""
        territories = []
        for _ in range(10):
            territories.append(Territory())

        first_id = min([t.id for t in territories])
        for i, territory in enumerate(territories):
            self.assertEqual(i + first_id, territory.id)

    def test_a_territory_is_land_by_default(self):
        """When the biome is not specified explicitly, land is assumed."""
        t = Territory()
        self.assertEqual(LandBiome, t.biome)

    def test_a_territory_without_units_is_neutral(self):
        """If a territory contains no units, it is neutral."""
        t = Territory()
        self.assertTrue(t.is_neutral())

    def test_a_territory_with_units_is_not_empty(self):
        """If a territory contains units, it is not empty.
        Note that this is different from that territory having an owner.
        The question that remains is whether a unit in a neutral land
        can have no owner -- not even Barbarian."""
        t = Territory()
        troop = Troop(territory=t)

        self.assertFalse(t.is_empty())

    def test_player_initialization_requires_only_name(self):
        """A player can be initialized only by name; other fields should have default values."""
        player = Player(name=self.faker.name())

        self.assertEqual("", player.description)
        self.assertEqual(0, player.influence_points)

    def test_player_names_cannot_be_reassigned(self):
        """A player, once initialized, cannot change his name. This is a requirement due to
        the fact that player hashing goes by name."""
        player = Player(name=self.faker.name())

        while True:
            new_name = self.faker.name()
            if player.name != new_name:
                break

        with self.assertRaises(AttributeError):
            player.name = new_name

    def test_troops_cavalry_and_generals_are_units(self):
        """A troop, cavalry or general are a type of unit and should be recognized as such."""
        troop = Troop(territory=Territory())
        cavalry = Cavalry(territory=Territory())
        general = General(territory=Territory())

        self.assertIsInstance(troop, Unit)
        self.assertIsInstance(cavalry, Unit)
        self.assertIsInstance(general, Unit)

    def test_unit_autoincrement_carries_between_unit_types(self):
        """If a new unit is created, the id is incremented, even if it is of a different unit type."""
        troop = Troop(territory=Territory())
        cavalry = Cavalry(territory=Territory())
        troop_2 = Troop(territory=Territory())

        self.assertEqual(troop.id + 1, cavalry.id)
        self.assertEqual(troop.id + 2, troop_2.id)

    def test_territory_take_a_random_unit(self):
        territory = Territory()
        troop = Troop(territory=territory)
        cavalry = Cavalry(territory=territory)

        self.assertEqual(troop, territory.take_unit(Troop))
        self.assertEqual(cavalry, territory.take_unit(Cavalry))

    def test_taking_more_units_than_present_is_rejected(self):
        territory = Territory()

        for i in range(10):
            Troop(territory=territory)

        with self.assertRaises(InsufficientUnitsException):
            territory.take_unit(Troop, 12)

    def test_taking_zero_units_is_permitted(self):
        territory = Territory()

        for i in range(10):
            Troop(territory=territory)

        self.assertEqual(set(), territory.take_unit(Troop, 0))

        empty_territory = Territory()
        self.assertEqual(set(), empty_territory.take_unit(Troop, 0))

    def test_taking_negative_units_is_rejected(self):
        territory = Territory()

        for i in range(10):
            Troop(territory=territory)

        with self.assertRaises(ValueError):
            territory.take_unit(Troop, -1)


if __name__ == "__main__":
    unittest.main()
