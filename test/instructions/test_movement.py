import unittest

from gd.excepts import (
    InstructionAlreadyExecuted,
    TargetTerritoryNotAdjacent,
    InsufficientUnitsException,
    IssuerDoesNotOwnTerritory,
)
from gd.mechanics import Phase, Turn, Movement, InstructionSet
from test.case import TestCase


class MovementTest(TestCase):
    def test_movement_with_other_origin_owner_is_invalid(self):
        p1, p2 = self.generate_players()
        t1, t2 = self.generate_territories(owners=[p2])
        self.generate_troops({t1: 1})

        order = Movement(issuer=p1, origin=t1, destination=t2, num_troops=1)

        with self.assertRaises(IssuerDoesNotOwnTerritory):
            order.assert_is_valid()

    def test_moving_all_units_away_keeps_the_origin_owner_the_same(self):
        p1, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[p1])
        self.generate_troops({t1: 3})
        Movement(issuer=p1, origin=t1, destination=t2, num_troops=3, instruction_set=InstructionSet()).execute()

        self.assertTerritoryHasTroops(t1, 0)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryHasTroops(t2, 3)
        self.assertTerritoryOwner(t2, p1)

    def test_movement_with_all_available_units_is_valid(self):
        p1, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[p1])
        self.generate_troops({t1: 3})
        instruction = Movement(issuer=p1, origin=t1, destination=t2, num_troops=3)
        instruction.assert_is_valid()

    def test_movement_with_insufficient_units_is_invalid(self):
        p1, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[p1])
        self.generate_troops({t1: 1})
        order = Movement(issuer=p1, origin=t1, destination=t2, num_troops=2)

        with self.assertRaises(InsufficientUnitsException):
            order.assert_is_valid()

    def test_movement_to_non_adjacent_territory_is_invalid(self):
        p1, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[p1], complete_graph=False)
        self.generate_troops({t1: 2})
        order = Movement(issuer=p1, origin=t1, destination=t2, num_troops=2)

        with self.assertRaises(TargetTerritoryNotAdjacent):
            order.assert_is_valid()

    def test_movement_can_be_executed_only_once(self):
        p1, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[p1])
        self.generate_troops({t1: 3})

        iset = InstructionSet()
        order = Movement(issuer=p1, origin=t1, destination=t2, num_troops=1, instruction_set=iset).execute()

        with self.assertRaises(InstructionAlreadyExecuted):
            order.execute()

    def test_expansion_to_an_empty_territory(self):
        p1, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[p1])
        self.generate_troops({t1: 10})
        Movement(issuer=p1, origin=t1, destination=t2, num_troops=6, instruction_set=InstructionSet()).execute()

        self.assertTerritoryOwner(t2, p1)
        self.assertTerritoryHasTroops(t1, 4)
        self.assertTerritoryHasTroops(t2, 6)

    def test_distributing_to_friendly_territory_costs_no_units(self):
        p1, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[p1, p1])
        self.generate_troops({t1: 10, t2: 6})

        Movement(issuer=p1, origin=t1, destination=t2, num_troops=5, instruction_set=InstructionSet()).execute()

        self.assertTerritoryHasTroops(t1, 5)
        self.assertTerritoryHasTroops(t2, 11)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryOwner(t2, p1)

    def test_simple_successful_invasion(self):
        p1, p2 = self.generate_players()
        t1, t2 = self.generate_territories(owners=[p1, p2])
        self.generate_troops({t1: 9, t2: 5})

        Movement(issuer=p1, origin=t1, destination=t2, num_troops=8, instruction_set=InstructionSet()).execute()

        self.assertTerritoryHasTroops(t1, 1)
        self.assertTerritoryHasTroops(t2, 1)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryOwner(t2, p1)

    def test_invasion_can_render_the_target_neutral(self):
        p1, p2 = self.generate_players()
        t1, t2 = self.generate_territories(owners=[p1, p2])
        self.generate_troops({t1: 6, t2: 3})

        Movement(issuer=p1, origin=t1, destination=t2, num_troops=5, instruction_set=InstructionSet()).execute()

        self.assertTerritoryHasTroops(t1, 1)
        self.assertTerritoryHasTroops(t2, 0)
        self.assertTerritoryOwner(t1, p1)
        self.assertTerritoryNeutral(t2)

    def test_invasion_to_empty_land_still_costs_penalty(self):
        p1, p2 = self.generate_players()
        t1, t2 = self.generate_territories(owners=[p1, p2])
        self.generate_troops({t1: 8, t2: 0})
        Movement(issuer=p1, origin=t1, destination=t2, num_troops=7, instruction_set=InstructionSet()).execute()

        # The troop penalty has been deducted from the 7 troops, but no further fighting took place.
        self.assertTerritoryHasTroops(t2, 5)
        self.assertTerritoryOwner(t2, p1)

    def test_mutual_invasion(self):
        p1, p2 = self.generate_players()
        t1, t2 = self.generate_territories(owners=[p1, p2])
        self.generate_troops({t1: 6, t2: 10})

        iset = InstructionSet()
        i1 = Movement(issuer=p1, origin=t1, destination=t2, num_troops=3, instruction_set=iset)
        i2 = Movement(issuer=p2, origin=t2, destination=t1, num_troops=3, instruction_set=iset)

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
        i1 = Movement(issuer=p1, origin=t1, destination=t3, num_troops=5, instruction_set=iset)
        i2 = Movement(issuer=p2, origin=t2, destination=t3, num_troops=2, instruction_set=iset)

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

        i1 = Movement(issuer=p1, origin=t1, destination=t4, num_troops=5, instruction_set=iset)
        i2 = Movement(issuer=p2, origin=t2, destination=t4, num_troops=2, instruction_set=iset)
        i3 = Movement(issuer=p3, origin=t3, destination=t4, num_troops=9, instruction_set=iset)

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
        p1, p2 = self.generate_players()
        t1, t2, t3 = self.generate_territories(owners=[p1, p1, p2])
        self.generate_troops({t1: 3, t2: 4, t3: 20})

        iset = InstructionSet()
        i1 = Movement(issuer=p1, origin=t1, destination=t3, num_troops=2, instruction_set=iset)
        Movement(issuer=p1, origin=t2, destination=t3, num_troops=3, instruction_set=iset)

        i1.execute()

        # Both movements have been executed
        self.assertTerritoryHasTroops(t1, 1)
        self.assertTerritoryHasTroops(t2, 1)

        # Invasion penalty applied only once
        self.assertTerritoryHasTroops(t3, 20-(5-2))

    def test_order_of_chain_of_invasions(self):
        p1, p2, p3 = self.generate_players(3)
        t1, t2, t3 = self.generate_territories(owners=[p1, p2, p3])
        self.generate_troops({t1: 6, t2: 6, t3: 6})

        iset = InstructionSet()
        i1 = Movement(issuer=p1, origin=t1, destination=t2, num_troops=4, instruction_set=iset)
        i2 = Movement(issuer=p2, origin=t2, destination=t3, num_troops=4, instruction_set=iset)

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

        i1 = Movement(issuer=p1, origin=t1, destination=t2, num_troops=4, instruction_set=iset)
        i2 = Movement(issuer=p2, origin=t2, destination=t3, num_troops=4, instruction_set=iset)
        i3 = Movement(issuer=p3, origin=t3, destination=t1, num_troops=4, instruction_set=iset)

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
        i1 = Movement(issuer=p1, origin=t1, destination=t2, num_troops=4, instruction_set=iset)
        i2 = Movement(issuer=p2, origin=t2, destination=t3, num_troops=4, instruction_set=iset)
        i3 = Movement(issuer=p3, origin=t3, destination=t1, num_troops=4, instruction_set=iset)

        # At this point, all instructions are valid: 4 troops are being moved and 5 are in the territory.
        # However, due to the circular resolve, instruction 1 kills some troops from territory 2, rendering
        # instruction 2 partially valid. This should be permitted.
        i1.execute()

    def test_a_turn_sorts_instructions_into_instruction_sets(self):
        p1, p2 = self.generate_players()
        t1, t2, t3, t4 = self.generate_territories(amount=4, owners=[p1, p2, p2, p2])

        invasion = Movement(issuer=p1, origin=t1, destination=t2, num_troops=4)
        second_invasion = Movement(issuer=p1, origin=t2, destination=t4, num_troops=4)
        distribution = Movement(issuer=p2, origin=t2, destination=t3, num_troops=1)
        distribution_2 = Movement(issuer=p2, origin=t2, destination=t4, num_troops=2)

        turn = Turn([invasion, second_invasion, distribution, distribution_2])

        self.assertEqual(1, len(turn.instruction_sets[Phase.MOVEMENT]))
        self.assertEqual(2, len(turn.instruction_sets[Phase.BATTLE]))
        self.assertEqual({distribution, distribution_2}, set(turn.instruction_sets[Phase.MOVEMENT][0].instructions))
        self.assertEqual({invasion}, set(turn.instruction_sets[Phase.BATTLE][0].instructions))
        self.assertEqual({second_invasion}, set(turn.instruction_sets[Phase.BATTLE][1].instructions))

    def test_a_turn_can_be_processed(self):
        p1, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[p1])
        self.generate_troops({t1: 10})

        movement = Movement(issuer=p1, origin=t1, destination=t2, num_troops=3)
        Turn([movement]).execute()

        self.assertTerritoryOwner(t2, p1)
        self.assertTrue(movement.is_executed)

    def test_movement_can_take_integers_instead_of_territories_if_world_is_set(self):
        p1, = self.generate_players(1)
        t1, t2 = self.generate_territories(owners=[p1])
        self.generate_troops({t1: 1})

        order = Movement(issuer=p1, origin=t1.id, destination=t2.id, num_troops=1, world=self.world)
        order.assert_is_valid()

        # Origin and destination are resolved to their respective Territories.
        self.assertEqual(order.origin, t1)
        self.assertEqual(order.destination, t2)


if __name__ == "__main__":
    unittest.main()
