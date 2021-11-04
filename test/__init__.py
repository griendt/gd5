def generate_name():
    return Faker().name().split(' ')[0]


def generate_players(amount: int = 2) -> list[Player]:
    return [Player(name=generate_name()) for _ in range(amount)]


def generate_territories(amount: int = 2, owners: list[Player] = None) -> list[Territory]:
    if owners is None:
        owners = [None for _ in range(amount)]

    if len(owners) < amount:
        # Pad the owner list with Nones if necessary
        owners += [None for _ in range(amount - len(owners))]

    return [Territory(owner=owner) for owner in owners]


def generate_troops(troops_by_territory: dict[Territory, int]) -> None:
    for territory, num_troops in troops_by_territory.items():
        for i in range(num_troops):
            Troop(territory=territory)

