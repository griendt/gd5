import unittest
from typing import Any

from faker import Faker

from excepts import InvalidInstruction, InstructionAlreadyExecuted
from logger import logger
from test.case import TestCase
from world import Instruction, Territory, Player, Troop, InstructionSet

name = Faker().name


class InstructionsTest(TestCase):
    def assertTerritoryHasTroops(self, territory: Territory, num_troops: int) -> None:
        self.assertEqual(num_troops, len(territory.all(Troop)))

    def assertTerritoryOwner(self, territory: Territory, player: Player) -> None:
        self.assertEqual(player, territory.owner)

    def assertTerritoryNeutral(self, territory: Territory) -> None:
        self.assertIsNone(territory.owner)

    def generate_players(self, amount: int = 2) -> list[Player]:
        return [Player(name=name()) for _ in range(amount)]

    def generate_territories(self, amount: int = 2, owners: list[Player] = None) -> list[Territory]:
        if owners is None:
            owners = [None for _ in range(amount)]

        if len(owners) < amount:
            # Pad the owner list with Nones if necessary
            owners += [None for _ in range(amount - len(owners))]

        return [Territory(owner=owner) for owner in owners]

    def generate_troops(self, troops_by_territory: dict[Territory, int]) -> None:
        for territory, num_troops in troops_by_territory.items():
            for i in range(num_troops):
                Troop(territory=territory)

    def test_instruction_with_other_origin_owner_is_invalid(self):
        p1, p2 = self.generate_players()
        t1, t2 = self.generate_territories(owners=[p2])
        self.generate_troops({t1: 1})

        order = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=1)

        with self.assertRaises(InvalidInstruction):
            order.assert_is_valid()

    def test_instruction_with_insufficient_units_is_invalid(self):
        p1, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[p1])
        self.generate_troops({t1: 1})
        order = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=1)

        with self.assertRaises(InvalidInstruction):
            order.assert_is_valid()

    def test_instruction_can_be_executed_only_once(self):
        p1, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[p1])
        self.generate_troops({t1: 3})

        iset = InstructionSet()
        order = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=1, instruction_set=iset).execute()

        with self.assertRaises(InstructionAlreadyExecuted):
            order.execute()

    def test_expansion_to_an_empty_territory(self):
        p1, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[p1])
        self.generate_troops({t1: 10})
        Instruction(issuer=p1, origin=t1, destination=t2, num_troops=6, instruction_set=InstructionSet()).execute()

        self.assertTerritoryOwner(t2, p1)
        self.assertTerritoryHasTroops(t1, 4)
        self.assertTerritoryHasTroops(t2, 6)

    def test_distributing_to_friendly_territory_costs_no_units(self):
        p1, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[p1, p1])
        self.generate_troops({t1: 10, t2: 6})

        Instruction(issuer=p1, origin=t1, destination=t2, num_troops=5, instruction_set=InstructionSet()).execute()

        self.assertTerritoryHasTroops(t1, 5)
        self.assertTerritoryHasTroops(t2, 11)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryOwner(t2, p1)

    def test_simple_successful_invasion(self):
        p1, p2 = self.generate_players()
        t1, t2 = self.generate_territories(owners=[p1, p2])
        self.generate_troops({t1: 9, t2: 5})

        Instruction(issuer=p1, origin=t1, destination=t2, num_troops=8, instruction_set=InstructionSet()).execute()

        self.assertTerritoryHasTroops(t1, 1)
        self.assertTerritoryHasTroops(t2, 1)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryOwner(t2, p1)

    def test_invasion_can_render_the_target_neutral(self):
        p1, p2 = self.generate_players()
        t1, t2 = self.generate_territories(owners=[p1, p2])
        self.generate_troops({t1: 6, t2: 3})

        Instruction(issuer=p1, origin=t1, destination=t2, num_troops=5, instruction_set=InstructionSet()).execute()

        self.assertTerritoryHasTroops(t1, 1)
        self.assertTerritoryHasTroops(t2, 0)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryNeutral(t2)

    def test_mutual_invasion(self):
        p1, p2 = self.generate_players()
        t1, t2 = self.generate_territories(owners=[p1, p2])
        self.generate_troops({t1: 6, t2: 10})

        iset = InstructionSet()
        i1 = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=3, instruction_set=iset)
        i2 = Instruction(issuer=p2, origin=t2, destination=t1, num_troops=3, instruction_set=iset)

        i1.execute()

        # The first Instruction in the mutual invasion has triggered the other Instruction as well,
        # due to the circular loop. Note that the Troop penalty should be incurred only once for each
        # Territory, hence, the second territory should have 4 Troops remaining (10 - 2 - (3-2) - 3).
        # The first territory is neutralized: 6 - 3 (invasion) - 3 (being invaded).
        self.assertTerritoryHasTroops(t1, 0)
        self.assertTerritoryHasTroops(t2, 4)
        self.assertTerritoryNeutral(t1)
        self.assertTerritoryOwner(t2, p2)
        self.assertTrue(i2.is_executed)

    def test_multiple_origin_skirmish_with_different_players(self):
        p1, p2, p3 = self.generate_players(3)
        t1, t2, t3 = self.generate_territories(owners=[p1, p2, p3])
        self.generate_troops({t1: 6, t2: 4, t3: 10})

        iset = InstructionSet()
        i1 = Instruction(issuer=p1, origin=t1, destination=t3, num_troops=5, instruction_set=iset)
        i2 = Instruction(issuer=p2, origin=t2, destination=t3, num_troops=2, instruction_set=iset)

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
        p1, p2, p3, p4 = self.generate_players(4)
        t1, t2, t3, t4 = self.generate_territories(owners=[p1, p2, p3, p4])
        self.generate_troops({t1: 6, t2: 3, t3: 10, t4: 1})

        iset = InstructionSet()

        i1 = Instruction(issuer=p1, origin=t1, destination=t4, num_troops=5, instruction_set=iset)
        i2 = Instruction(issuer=p2, origin=t2, destination=t4, num_troops=2, instruction_set=iset)
        i3 = Instruction(issuer=p3, origin=t3, destination=t4, num_troops=9, instruction_set=iset)

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
        p1, p2 = self.generate_players()
        t1, t2, t3 = self.generate_territories(owners=[p1, p1, p2])
        self.generate_troops({t1: 3, t2: 4, t3: 20})

        iset = InstructionSet()
        i1 = Instruction(issuer=p1, origin=t1, destination=t3, num_troops=2, instruction_set=iset)
        Instruction(issuer=p1, origin=t2, destination=t3, num_troops=3, instruction_set=iset)

        i1.execute()

        raise NotImplementedError

    def test_order_of_chain_of_invasions(self):
        p1, p2, p3 = self.generate_players(3)
        t1, t2, t3 = self.generate_territories(owners=[p1, p2, p3])
        self.generate_troops({t1: 6, t2: 6, t3: 6})

        iset = InstructionSet()
        i1 = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=4, instruction_set=iset)
        i2 = Instruction(issuer=p2, origin=t2, destination=t3, num_troops=4, instruction_set=iset)

        i1.execute()

        self.assertTerritoryHasTroops(t1, 2)
        self.assertTrue(i1.is_executed)
        self.assertTrue(i2.is_executed)
        self.assertTerritoryHasTroops(t2, 0)
        self.assertTerritoryHasTroops(t3, 4)

    def test_circular_invasions(self):
        p1, p2, p3 = self.generate_players(3)
        t1, t2, t3 = self.generate_territories(owners=[p1, p2, p3])
        self.generate_troops({t1: 5, t2: 20, t3: 20})
        iset = InstructionSet()

        i1 = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=4, instruction_set=iset)
        i2 = Instruction(issuer=p2, origin=t2, destination=t3, num_troops=4, instruction_set=iset)
        i3 = Instruction(issuer=p3, origin=t3, destination=t1, num_troops=4, instruction_set=iset)

        i1.execute()

        self.assertTrue(i1.is_executed)
        self.assertTrue(i3.is_executed)
        self.assertTrue(i2.is_executed)
        # First, player 1 slays 2 troops of player 2 with 4 units, leaving 18 in territory 2 and one in territory 1.
        # Then, player 2 slays 2 troops of player 3, leaving 14 in territory 2 and 18 in territory 3.
        # Finally, player 3 slays the remaining troop of player 1 and overtakes territory 1 with one troop.
        self.assertTerritoryHasTroops(t2, 14)
        self.assertTerritoryHasTroops(t3, 14)
        self.assertTerritoryHasTroops(t1, 1)
        self.assertTerritoryOwner(t1, p3)

    def test_invasion_can_be_rendered_partial_by_circular_invasions(self):
        p1, p2, p3 = self.generate_players(3)
        t1, t2, t3 = self.generate_territories(owners=[p1, p2, p3])
        self.generate_troops({t1: 5, t2: 5, t3: 5})

        iset = InstructionSet()
        i1 = Instruction(issuer=p1, origin=t1, destination=t2, num_troops=4, instruction_set=iset)
        i2 = Instruction(issuer=p2, origin=t2, destination=t3, num_troops=4, instruction_set=iset)
        i3 = Instruction(issuer=p3, origin=t3, destination=t1, num_troops=4, instruction_set=iset)

        # At this point, all instructions are valid: 4 troops are being moved and 5 are in the territory.
        # However, due to the circular resolve, instruction 1 kills some troops from territory 2, rendering
        # instruction 2 partially valid. This should be permitted.
        i1.execute()

    # TODO: add partially rendered invasion situation in case of a conditional, e.g. a player moving from 1 to 2 to 3 in one turn
    #   and territory 2 was fortified before the first attack. However this also demands that non-invasion moves were executed before invasions,
    #   which is not yet implemented either.


if __name__ == "__main__":
    unittest.main()
