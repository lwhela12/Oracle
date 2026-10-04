# Celestial motion study

An isolated, local visual direction for Oracle astrology: a fine silver-blue star field
flows in broad currents, then gathers around calculated planet positions. It is not
connected to the production interface or to a model API.

From the repository root:

```sh
scratch/astrology-venv/bin/python -m http.server 8883 --bind 127.0.0.1 --directory experiments/astrology/motion-study
```

Open http://127.0.0.1:8883/. Form/release the chart, pause the animation, and select any
planet to inspect its placement and highlight major aspects. Planet controls are ordinary
keyboard-accessible buttons. The canvas is decorative; placements remain available as text.

`chart.js` contains a fixed global reference sky calculated by `astrology.engine.calculate_sky`
for **2000-01-01T12:00:00Z**. It contains no private birth data. Planet longitudes and
aspects are calculated; radial spacing and surrounding particles are expressive. This is
a map of zodiac longitudes, not a perspective view of the solar system or a star catalogue.

The visual reference is the user's description of the [Astra launch page](https://openai.com/index/gpt-6-astra/).
The page's interactive star field was identifiable in its accessibility tree, but its
animation could not be reliably rendered in the embedded browser. All graphics here are
original procedural drawing; no reference assets or implementation were copied.

The motion renderer respects reduced motion and tab visibility, caps particle count and
display resolution, and provides a pause control. Real device performance still needs
qualification before integrating this treatment into the main application.
