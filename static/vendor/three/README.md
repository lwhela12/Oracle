three.js r160 (npm three@0.160.0), build/three.module.min.js and the examples/jsm
postprocessing files under addons/ needed for bloom, all unmodified. MIT licence in LICENSE.
Vendored so the 3D sanctum prototype does not depend on a CDN. Addons import the bare
specifier "three", resolved by the import map in static/sanctum/index.html.
