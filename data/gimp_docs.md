# Borders

## Land/water borders
On a copy of the land mass:
 - remove alpha channel
 - Filters -> Edge -> Difference of Guassians with radius 0 and 5 respectively
 - Colours -> Treshold (set to 100 for semi-thick border; higher for thinner; 100 is used for coastal borders)
 - Select by Colour Tool (right click magic wand) -> remove all black
 - Colours -> Invert to have a black border

For the water effect:
 - Select boundary by colour
 - Grow selection by 3 pixels
 - Fill with black
 - Shrink selection by 1 pixel
 - Delete
 - Set the opacity of the outline layer as desired (for coast: 75%, 50%, 25%).

## Territory borders
 - Use a circular 3 pixel __pencil__ brush to draw the border

# Territory names
 - Each territory is a layer
 - Use font Yrsa Bold 90 with a bright color (e.g. #F00)
 - Duplicate the layer group to a new group and merge it
 - Filters -> Emboss:
   - Azimuth 45
   - Elevation 30
   - Depth 100
 - Colour -> Colour Temperature:
   - Original temperature 6500K
   - Intended temperature 12000K
 - Colour -> Saturation:
   - Scale 2.000
 - Colour -> Hue-Chroma:
   - Hue -60
   - Chroma 100
   - Lightness 0

# HQ names
 - Same as Territory names, but with the following on top
 - Colour -> Hue-Chroma:
   - Hue 60
   - Chroma 0
   - Lightness 30
 - Drop Shadow:
   - X: 2
   - Y: 2
   - Blur radius 0
   - Grow radius 2
   - Color #000
   - Opacity 0.5
   - Keep Blending Options intact

# HQ Flags
 - Start with the HQ base layer
 - Select the colour of the corresponding land territory
 - Magic Wand tool with threshold 140 -> Select the flag (white portion)
 - Colourise
   - Saturation to 0.8
   - Lightness to -0.6
 - After all HQs are made, duplicate them all and merge them into a single layer
   - Drop Shadow
     - X: 0
     - Y: 0
     - Blur radius 0
     - Grow radius 2
     - Opacity 2.0
   
# Barbarians
 - Territory color: #B5B5A5

# Wastelands
 - Use the fill tool with the "Dried Mud" pattern fill
 - Colours -> Treshold
   - Set the __white__ to 200
 - Make sure the layer has opacity 50%