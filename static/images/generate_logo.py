#!/usr/bin/env python3
"""
Generate the Nostr Market logo.
Requires: pip install Pillow
"""

from PIL import Image, ImageDraw  # type: ignore[import-not-found]

# Render at 4x size for antialiasing
scale = 4
size = 128 * scale
final_size = 128

# Consistent color scheme with Nostr Proxy
dark_purple = (80, 40, 120)
light_purple = (140, 100, 180)
white = (255, 255, 255)

margin = 4 * scale

swoosh_center = ((128 + 100) * scale, -90 * scale)
swoosh_radius = 220 * scale

# Create rounded rectangle mask
mask = Image.new("L", (size, size), 0)
mask_draw = ImageDraw.Draw(mask)
corner_radius = 20 * scale
mask_draw.rounded_rectangle(
    [margin, margin, size - margin, size - margin],
    radius=corner_radius,
    fill=255,
)

# Create background with swoosh
bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
bg_draw = ImageDraw.Draw(bg)
bg_draw.rounded_rectangle(
    [margin, margin, size - margin, size - margin],
    radius=corner_radius,
    fill=dark_purple,
)
bg_draw.ellipse(
    [
        swoosh_center[0] - swoosh_radius,
        swoosh_center[1] - swoosh_radius,
        swoosh_center[0] + swoosh_radius,
        swoosh_center[1] + swoosh_radius,
    ],
    fill=light_purple,
)

# Apply rounded rectangle mask
final = Image.new("RGBA", (size, size), (0, 0, 0, 0))
final.paste(bg, mask=mask)
draw = ImageDraw.Draw(final)

center_x, center_y = size // 2, size // 2

# Shop/storefront - wider and shorter for shop look
shop_width = 80 * scale
awning_height = 18 * scale
body_height = 45 * scale
total_height = awning_height + body_height

shop_left = center_x - shop_width // 2
shop_right = center_x + shop_width // 2

# Center vertically
awning_top = center_y - total_height // 2
awning_bottom = awning_top + awning_height
shop_bottom = awning_bottom + body_height
awning_extend = 5 * scale

# Draw awning background (white base)
draw.rectangle(
    [shop_left - awning_extend, awning_top, shop_right + awning_extend, awning_bottom],
    fill=white,
)

# Vertical stripes on awning (alternating dark purple)
stripe_count = 8
stripe_width = (shop_width + 2 * awning_extend) // stripe_count
for i in range(1, stripe_count, 2):
    x_left = shop_left - awning_extend + i * stripe_width
    draw.rectangle(
        [x_left, awning_top, x_left + stripe_width, awning_bottom],
        fill=dark_purple,
    )

# Shop body (below awning)
draw.rectangle(
    [shop_left, awning_bottom, shop_right, shop_bottom],
    fill=white,
)

# Large display window (shop style)
window_margin = 8 * scale
window_top = awning_bottom + 6 * scale
window_bottom = shop_bottom - 6 * scale
# Left display window
draw.rectangle(
    [shop_left + window_margin, window_top, center_x - 10 * scale, window_bottom],
    fill=dark_purple,
)
# Right display window
draw.rectangle(
    [center_x + 10 * scale, window_top, shop_right - window_margin, window_bottom],
    fill=dark_purple,
)

# Door (center, dark purple cutout)
door_width = 14 * scale
door_left = center_x - door_width // 2
draw.rectangle(
    [door_left, window_top, door_left + door_width, shop_bottom],
    fill=dark_purple,
)

# Downscale with LANCZOS for antialiasing
final = final.resize((final_size, final_size), Image.LANCZOS)

final.save("nostr-market.png")
print("Logo saved to nostr-market.png")
