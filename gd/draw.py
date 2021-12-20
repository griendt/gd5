from PIL import Image, ImageDraw, ImageFont

coordinates = {
    2: (610, 630),
    5: (650, 1070),
    10: (660, 1420),
    17: (1360, 1260),
    30: (2060, 1030),
    37: (3000, 740),
    42: (2960, 1130),
    48: (2230, 1370),
    49: (2500, 1520),
    66: (3580, 740),
    77: (3200, 1560),
    80: (3370, 1640),
    "Benarus": (3440, 1040),
    "Bevon Sandbag": (3380, 280),
    "Kruppach": (2100, 1700),
    "Lancre": (3640, 670),
    "Mojo": (420, 1160),
    "Orion": (1460, 660),
    "Pyronia": (350, 1920),
    "Schism": (2650, 500),
    "Vermillion": (3200, 1680),
}

world_map = Image.open('./data/maps/map0-6.png')
font = ImageFont.truetype("./data/font.ttf", 40)
drawer = ImageDraw.Draw(world_map)
troop_icon = Image.open('./data/troop.png').convert('RGBA').resize((64, 64))


def draw_coordinates():
    for territory_identifier, (x, y) in coordinates.items():
        draw_troops((x, y), 12)
    world_map.save("./data/maps/map-edited.png")


def draw_troops(xy: tuple[int, int], num_troops: int = None):
    world_map.paste(troop_icon, (xy[0] - troop_icon.size[0] // 2, xy[1] - troop_icon.size[1] // 2), troop_icon)
    if num_troops:
        drawer.text((xy[0], xy[1] - 2), str(num_troops), font=font, anchor="mm", fill="black", stroke_fill="white", stroke_width=2)