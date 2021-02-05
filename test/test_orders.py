import unittest

from faker import Faker

from data.exceptions import InvalidInstruction, InstructionAlreadyExecuted
from data.world import Instruction, Territory, Player, Troop


class InstructionsTest(unittest.TestCase):
    faker = Faker()

    def assertTerritoryHasTroops(self, territory: Territory, num_troops: int) -> None:
        self.assertEqual(num_troops, len(territory.units_of(Troop)))

    def assertTerritoryOwner(self, territory: Territory, player: Player) -> None:
        self.assertEqual(player, territory.owner)

    def test_instruction_with_other_origin_owner_is_invalid(self):
        p1, p2 = Player(name=self.faker.name()), Player(name=self.faker.name())
        t1, t2 = Territory(owner=p2), Territory()

        Troop(territory=t1)
        order = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=1)

        with self.assertRaises(InvalidInstruction):
            order.assert_is_valid()

    def test_instruction_with_insufficient_units_is_invalid(self):
        p1 = Player(name=self.faker.name())
        t1, t2 = Territory(owner=p1), Territory()

        Troop(territory=t1)
        order = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=2)

        with self.assertRaises(InvalidInstruction):
            order.assert_is_valid()

    def test_instruction_can_be_executed_only_once(self):
        p1 = Player(name=self.faker.name())
        t1, t2 = Territory(owner=p1), Territory()

        Troop(territory=t1)
        Troop(territory=t1)

        order = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=1).execute()

        with self.assertRaises(InstructionAlreadyExecuted):
            order.execute()

    def test_expansion_to_an_empty_territory(self):
        p1 = Player(name=self.faker.name())
        t1, t2 = Territory(owner=p1), Territory()

        for i in range(10):
            Troop(territory=t1)

        Instruction(issuer=p1, origin=t1, destination=t2, num_troops=6).execute()

        self.assertEqual(p1, t2.owner)
        self.assertEqual(4, len(t1.units_of(Troop)))
        self.assertEqual(6, len(t2.units_of(Troop)))

    def test_distributing_to_friendly_territory_costs_no_units(self):
        p1 = Player(name=self.faker.name())
        t1, t2 = Territory(owner=p1), Territory(owner=p1)

        for i in range(10):
            Troop(territory=t1)

        for i in range(6):
            Troop(territory=t2)

        Instruction(issuer=p1, origin=t1, destination=t2, num_troops=5).execute()

        self.assertEqual(5, len(t1.units_of(Troop)))
        self.assertEqual(11, len(t2.units_of(Troop)))
        self.assertEqual(p1, t1.owner)
        self.assertEqual(p1, t2.owner)


if __name__ == "__main__":
    unittest.main()
