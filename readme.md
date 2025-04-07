# Colour Magnitude rewrite

This is a "Fan"-rewrite of the colour magnitude program of Astrophysics of CAU Kiel.
I did not do any of the fancy "maths"-stuff, but tried to put the existing functionality into a more user friendly
framework.

## Usage

- Create input_cmd.toml like former input_cmd.dat, just... as toml
- After loading use mouse wheel to zoom into canvas
- All found stars are selected for processing by default (green ellipse)
- Use __left mouse button__ to toggle selection of a single star (red ellipse: deselected)
- Use __shift__ and __drag left mouse button__ to toggle selection of multiple stars at once
- Use __ctrl__ and __drag left mouse button__ to move canvas around (when zoomed in)
- Use __right mouse button__ on a star to define magnitudes (blue ellipse: labeled star)
  - to "un-label" a star, use __right mouse button__ and set both values to 0
- Labeled, but deselected stars will appear orange