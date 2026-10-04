# Third-party notices

Astrology uses unmodified JPL DE440s data and the independently licensed Skyfield,
jplephem, NumPy, sgp4, certifi and GeoNamesCache packages. Their copyright notices,
license terms and source links are preserved in
[the astronomy notice bundle](static/astrology/THIRD_PARTY_NOTICES.txt), also linked
from the astrology page. The NumPy notice is from the pinned Linux x86_64 wheel
used by the release platform, including its bundled libraries and exceptions.
Installed dependencies retain their original distribution metadata/licenses.

Original code under `astrology/jpl/` is separately identified by its LICENSE.
This does not claim ownership of JPL data or third-party implementations. The
release does not ship the optional Swiss binding or comparison engine.

Existing PDF/font notices remain under `static/vendor/pdfmake/`. GeoNames
administrative-region source information is in `astrology/data/admin1.SOURCE.md`.
Other application dependencies retain their upstream licenses; this file does
not replace or change those licenses.
