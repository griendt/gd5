from faker import Faker


def generate_name():
    return Faker().name().split(' ')[0]
