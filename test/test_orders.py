import unittest
from typing import Any

from faker import Faker

from excepts import InvalidInstruction, InstructionAlreadyExecuted
from logger import logger
from world import Instruction, Territory, Player, Troop, InstructionSet


class InstructionsTest(unittest.TestCase):
    faker = Faker()

    def setUp(self) -> None:
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
        order = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=1)

        with self.assertRaises(InvalidInstruction):
            order.assert_is_valid()

    def test_instruction_can_be_executed_only_once(self):
        p1 = Player(name=self.faker.name())
        t1, t2 = Territory(owner=p1), Territory()
        iset = InstructionSet()

        Troop(territory=t1)
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

        for i in range(9):
            Troop(territory=t1)

        for i in range(5):
            Troop(territory=t2)

        Instruction(issuer=p1, origin=t1, destination=t2, num_troops=8, instruction_set=iset).execute()

        self.assertTerritoryHasTroops(t1, 1)
        self.assertTerritoryHasTroops(t2, 1)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryOwner(t2, p1)

    def test_invasion_can_render_the_target_neutral(self):
        p1, p2 = Player(name=self.faker.name()), Player(name=self.faker.name())
        t1, t2 = Territory(owner=p1), Territory(owner=p2)
        iset = InstructionSet()

        for i in range(6):
            Troop(territory=t1)

        for i in range(3):
            Troop(territory=t2)

        Instruction(issuer=p1, origin=t1, destination=t2, num_troops=5, instruction_set=iset).execute()

        self.assertTerritoryHasTroops(t1, 1)
        self.assertTerritoryHasTroops(t2, 0)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryNeutral(t2)

    def test_mutual_invasion(self):
        p1, p2 = Player(name=self.faker.name()), Player(name=self.faker.name())
        t1, t2 = Territory(owner=p1), Territory(owner=p2)
        iset = InstructionSet()
        i1 = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=3, instruction_set=iset)
        i2 = Instruction(issuer=p2, origin=t2, destination=t1, num_troops=3, instruction_set=iset)

        for i in range(6):
            Troop(territory=t1)

        for i in range(10):
            Troop(territory=t2)

        i1.execute()

        # The first Instruction in the mutual invasion has triggered both Troop penalties.
        # Hence, the target has 10 - 2 - (3-2) = 7 troops left.
        self.assertTerritoryHasTroops(t1, 3)
        self.assertTerritoryHasTroops(t2, 7)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryOwner(t2, p2)

        # In executing the first order, the second order involved was not processed automatically!
        self.assertFalse(i2.is_executed)

        i2.execute()
        # The Troop penalty should not occur another time; only the normal flow of the battle should continue.
        self.assertTerritoryHasTroops(t1, 0)
        self.assertTerritoryHasTroops(t2, 4)
        self.assertTerritoryNeutral(t1)
        self.assertTerritoryOwner(t2, p2)
        self.assertTrue(i2.is_executed)

    def test_multiple_origin_skirmish_with_different_players(self):
        p1, p2, p3 = Player(name=self.faker.name()), Player(name=self.faker.name()), Player(name=self.faker.name())
        t1, t2, t3 = Territory(owner=p1), Territory(owner=p2), Territory(owner=p3)
        iset = InstructionSet()

        i1 = Instruction(issuer=p1, origin=t1, destination=t3, num_troops=5, instruction_set=iset)
        i2 = Instruction(issuer=p2, origin=t2, destination=t3, num_troops=2, instruction_set=iset)

        for i in range(6):
            Troop(territory=t1)

        for i in range(4):
            Troop(territory=t2)

        for i in range(10):
            Troop(territory=t3)

        i1.execute()

        # There is a skirmish between Player 1 and Player 2, even though Player 3 is the one whose territory
        # is being attacked. Both troops from player 2 that were sent should be destroyed by Player 1, and
        # the remainder of Player 1's troops should trigger an invasion to Player 3's territory.
        self.assertTerritoryHasTroops(t1, 1)
        self.assertTerritoryHasTroops(t2, 2)

        # Player 1 should have 3 of its 5 units remaining that go onward to invade.
        # This means one of Player 3's troops is expected to be slain.
        self.assertTerritoryHasTroops(t3, 9)

        # In executing the first order, the second order involved in the skirmish was also executed automatically.
        self.assertTrue(i2.is_executed)

    def test_triple_skirmish_with_three_players(self):
        p1, p2, p3, p4 = Player(name=self.faker.name()), Player(name=self.faker.name()), Player(name=self.faker.name()), Player(name=self.faker.name())
        t1, t2, t3, t4 = Territory(owner=p1), Territory(owner=p2), Territory(owner=p3), Territory(owner=p4)
        iset = InstructionSet()

        i1 = Instruction(issuer=p1, origin=t1, destination=t4, num_troops=5, instruction_set=iset)
        i2 = Instruction(issuer=p2, origin=t2, destination=t4, num_troops=2, instruction_set=iset)
        i3 = Instruction(issuer=p3, origin=t3, destination=t4, num_troops=9, instruction_set=iset)

        for i in range(6):
            Troop(territory=t1)

        for i in range(3):
            Troop(territory=t2)

        for i in range(10):
            Troop(territory=t3)

        for i in range(1):
            Troop(territory=t4)

        # FIXME: This test passes because we execute the instruction with the biggest army set.
        #   This should not be relevant.
        i3.execute()

        # All attackers have sent the maximum number of troops they had available.
        self.assertTerritoryHasTroops(t1, 1)
        self.assertTerritoryHasTroops(t2, 1)
        self.assertTerritoryHasTroops(t3, 1)

        # Notice that in the skirmishes, all troops are to be vanquished save 4 of Player 3's troops.
        # These 4 troops then go on to invade the single troop in t4 and take over.
        self.assertTerritoryHasTroops(t4, 1)
        self.assertTerritoryOwner(t4, p3)

        # In resolving the skirmishes, all orders are finalized.
        self.assertTrue(i1.is_executed)
        self.assertTrue(i2.is_executed)
        self.assertTrue(i3.is_executed)

    def test_simple_invasion_from_multiple_origins(self):
        self.skipTest('Need to properly define the spec of multi-origin invasions')
        p1, p2 = Player(name=self.faker.name()), Player(name=self.faker.name())
        t1, t2, t3 = Territory(owner=p1), Territory(owner=p1), Territory(owner=p2)
        iset = InstructionSet()

        i1 = Instruction(issuer=p1, origin=t1, destination=t3, num_troops=2, instruction_set=iset)
        Instruction(issuer=p1, origin=t2, destination=t3, num_troops=3, instruction_set=iset)

        for i in range(3):
            Troop(territory=t1)

        for i in range(4):
            Troop(territory=t2)

        for i in range(20):
            Troop(territory=t3)

        i1.execute()

        raise NotImplementedError

    def test_order_of_chain_of_invasions(self):
        self.skipTest("Chain of invasions not yet implemented")
        p1, p2, p3 = Player(name=self.faker.name()), Player(name=self.faker.name()), Player(name=self.faker.name())
        t1, t2, t3 = Territory(owner=p1), Territory(owner=p2), Territory(owner=p3)
        iset = InstructionSet()

        i1 = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=4, instruction_set=iset)
        i2 = Instruction(issuer=p2, origin=t2, destination=t3, num_troops=4, instruction_set=iset)

        for i in range(6):
            Troop(territory=t1)
            Troop(territory=t2)
            Troop(territory=t3)

        i1.execute()

        self.assertTerritoryHasTroops(t1, 2)
        self.assertTrue(i1.is_executed)
        self.assertTrue(i2.is_executed)
        self.assertTerritoryHasTroops(t2, 0)
        self.assertTerritoryHasTroops(t3, 4)

    def test_circular_invasions(self):
        self.skipTest("Circular invasion detection not yet implemented")
        p1, p2, p3 = Player(name=self.faker.name()), Player(name=self.faker.name()), Player(name=self.faker.name())
        t1, t2, t3 = Territory(owner=p1), Territory(owner=p2), Territory(owner=p3)
        iset = InstructionSet()

        i1 = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=4, instruction_set=iset)
        i2 = Instruction(issuer=p2, origin=t2, destination=t3, num_troops=4, instruction_set=iset)
        i3 = Instruction(issuer=p3, origin=t3, destination=t1, num_troops=4, instruction_set=iset)

        for i in range(6):
            Troop(territory=t1)
            Troop(territory=t2)
            Troop(territory=t3)

        i1.execute()

        self.assertTrue(i1.is_executed)
        self.assertTrue(i3.is_executed)
        self.assertTrue(i2.is_executed)
        # First, player 1 slays 2 troops of player 2 with 4 units.
        # Then, player 3 slays 2 troops of player 1, rendering territory 1 neutral.
        # Finally, player 2 can only use 3 of its 4 remaining units to attack, slaying 1 troop of player 3.
        # This means player 1 is neutral, and players 2 and 3 each have one unit remaining.
        self.assertTerritoryHasTroops(t1, 0)
        self.assertTerritoryHasTroops(t2, 1)
        self.assertTerritoryHasTroops(t3, 1)


if __name__ == "__main__":
    unittest.main()
