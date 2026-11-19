# Local browser dependencies

The prototype intentionally bundles its browser dependencies for offline presentation.
No CDN connection is required to view charts or mathematics.

| Component | Version | License | Local notice |
| --- | --- | --- | --- |
| Plotly.js | 2.35.3 | MIT | dist/vendor/PLOTLY_LICENSE |
| KaTeX JavaScript, CSS and bundled fonts | 0.16.11 | MIT, with upstream font notices | dist/vendor/KATEX_LICENSE; dist/vendor/KATEX_FONTS_LICENSE |

Plotly distribution: https://www.npmjs.com/package/plotly.js-dist-min/v/2.35.3

KaTeX: https://github.com/KaTeX/KaTeX/tree/v0.16.11

KaTeX CSS was reduced to its WOFF2 font sources; the included fonts, JavaScript and
mathematical rendering are otherwise unmodified. Modern Chrome, Edge and Firefox
support WOFF2.

Python packages are installed from the versions in requirements.txt and are not
redistributed as package source inside the ZIP. Their respective upstream licenses
apply. The unchanged UCI dataset is separately attributed in DATA_LICENSE.md.
