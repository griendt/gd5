import unittest

from faker import Faker

from excepts import InvalidInstruction, InstructionAlreadyExecuted
from world import Instruction, Territory, Player, Troop, InstructionSet


class InstructionsTest(unittest.TestCase):
    faker = Faker()

    def assertTerritoryHasTroops(self, territory: Territory, num_troops: int) -> None:
        self.assertEqual(num_troops, len(territory.all(Troop)))

    def assertTerritoryOwner(self, territory: Territory, player: Player) -> None:
        self.assertEqual(player, territory.owner)

    def assertTerritoryNeutral(self, territory: Territory) -> None:
        self.assertIsNone(territory.owner)

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
        iset = InstructionSet()

        Troop(territory=t1)
        Troop(territory=t1)

        order = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=1, instruction_set=iset).execute()

        with self.assertRaises(InstructionAlreadyExecuted):
            order.execute()

    def test_expansion_to_an_empty_territory(self):
        p1 = Player(name=self.faker.name())
        t1, t2 = Territory(owner=p1), Territory()
        iset = InstructionSet()

        for i in range(10):
            Troop(territory=t1)

        Instruction(issuer=p1, origin=t1, destination=t2, num_troops=6, instruction_set=iset).execute()

        self.assertTerritoryOwner(t2, p1)
        self.assertTerritoryHasTroops(t1, 4)
        self.assertTerritoryHasTroops(t2, 6)

    def test_distributing_to_friendly_territory_costs_no_units(self):
        p1 = Player(name=self.faker.name())
        t1, t2 = Territory(owner=p1), Territory(owner=p1)
        iset = InstructionSet()

        for i in range(10):
            Troop(territory=t1)

        for i in range(6):
            Troop(territory=t2)

        Instruction(issuer=p1, origin=t1, destination=t2, num_troops=5, instruction_set=iset).execute()

        self.assertTerritoryHasTroops(t1, 5)
        self.assertTerritoryHasTroops(t2, 11)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryOwner(t2, p1)

    def test_simple_successful_invasion(self):
        p1, p2 = Player(name=self.faker.name()), Player(name=self.faker.name())
        t1, t2 = Territory(owner=p1), Territory(owner=p2)
        iset = InstructionSet()

        for i in range(8):
            Troop(territory=t1)

        for i in range(5):
            Troop(territory=t2)

        Instruction(issuer=p1, origin=t1, destination=t2, num_troops=7, instruction_set=iset).execute()

        self.assertTerritoryHasTroops(t1, 1)
        self.assertTerritoryHasTroops(t2, 1)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryOwner(t2, p1)

    def test_invasion_can_render_the_target_neutral(self):
        p1, p2 = Player(name=self.faker.name()), Player(name=self.faker.name())
        t1, t2 = Territory(owner=p1), Territory(owner=p2)
        iset = InstructionSet()

        for i in range(5):
            Troop(territory=t1)

        for i in range(3):
            Troop(territory=t2)

        Instruction(issuer=p1, origin=t1, destination=t2, num_troops=4, instruction_set=iset).execute()

        self.assertTerritoryHasTroops(t1, 1)
        self.assertTerritoryHasTroops(t2, 0)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryNeutral(t2)

    def test_simple_skirmish_mutual_invasion(self):
        p1, p2 = Player(name=self.faker.name()), Player(name=self.faker.name())
        t1, t2 = Territory(owner=p1), Territory(owner=p2)
        iset = InstructionSet()
        i1 = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=3, instruction_set=iset)
        i2 = Instruction(issuer=p2, origin=t2, destination=t1, num_troops=3, instruction_set=iset)

        for i in range(6):
            Troop(territory=t1)

        for i in range(4):
            Troop(territory=t2)

        i1.execute()

        # All units involved in the skirmish were lost.
        self.assertTerritoryHasTroops(t1, 3)
        self.assertTerritoryHasTroops(t2, 1)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryOwner(t2, p2)

        # In executing the first order, the second order involved in the skirmish was also executed automatically.
        self.assertTrue(i2.is_executed)


if __name__ == "__main__":
    unittest.main()
