# Colour Magnitude rewrite

This is a "Fan"-rewrite of the colour magnitude program of Astrophysics of CAU Kiel.
I did not do any of the fancy "maths"-stuff, but tried to put the existing functionality into a more user friendly
framework.

## Requirements

- Python Version 3.12 or higher
- Package-dependencies: see [requirements.txt](requirements.txt)

## Usage

- setup by defining values in [input_cmd.toml](input_cmd.toml) in the same directory as main.py
- Have data ready at paths defined in input_cmd.toml
- Run
```shell
python main.py
```

## input_cmd.toml

- Paths for fits files (String, multiple files allowed in one directory):
  - path_light_short = "./data/colour/blue/"
  - path_light_long
  - path_dark_short
  - path_dark_long
  - path_flat_short
  - path_flat_long
  - path_dark_flat

- Output directory (String):
  - path_result

- Flags for corrections (Booleans):
  - do_dark: Dark correction (uses path_dark_short and path_dark_long)
  - do_flat: Flat field correction (uses path_flat_short and path_flat_long)
  - do_dark_flat: Dark correction for flat fields (uses path_dark_flat)

- Names for colour (Strings, for labels during plotting):
  - short_colour: Name for short wave colour
  - long_colour: Name for long wave colour

- Position in degrees of the observatory (Float, optional):
  - longitude = 10.112354
  - latitude  = 54.347889

- Data (float):
  - FWHM: FWHM of the major axis of stars (2D-Gaussian) in pixels; one pixel w/o binning ~0.9 arcseconds; typical seeing conditions ~2-4 arcseconds
  - ratio: ratio of FWHM_minor and FWHM_major; 1.0 means circular Gaussian
  - threshold: threshold * std = detection threshold for star finding algorithm; std is standard deviation of the sky background, i.e., read out noise + dark current noise
  - r_aperture: radius of the circular aperture to count star flux, in units of FWHM; theoretically as large as possible, but possible contamination of other stars nearby
