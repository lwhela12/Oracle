window.ORACLE_SKY_STUDY = {
  "engine": {
    "library": "Swiss Ephemeris",
    "library_version": "2.10.03",
    "binding": "pysweph",
    "binding_version": "2.10.3.6",
    "ephemeris_model": "Moshier analytical ephemeris (explicit)"
  },
  "provenance": {
    "coordinate_model": "apparent geocentric tropical ecliptic longitudes of date",
    "time_conversion": "UTC via swe.utc_to_jd; calc_ut uses UT1",
    "planetary_flags_requested": 260,
    "planetary_flags_returned": {
      "Sun": 260,
      "Moon": 260,
      "Mercury": 260,
      "Venus": 260,
      "Mars": 260,
      "Jupiter": 260,
      "Saturn": 260,
      "Uranus": 260,
      "Neptune": 260,
      "Pluto": 260
    },
    "aspect_orbs_degrees": {
      "conjunction": {
        "angle": 0.0,
        "orb": 8.0
      },
      "sextile": {
        "angle": 60.0,
        "orb": 5.0
      },
      "square": {
        "angle": 90.0,
        "orb": 7.0
      },
      "trine": {
        "angle": 120.0,
        "orb": 7.0
      },
      "opposition": {
        "angle": 180.0,
        "orb": 8.0
      }
    },
    "warnings": [],
    "sources": [
      "https://www.astro.com/swisseph/swephprg.htm",
      "https://github.com/astrorigin/pyswisseph/tree/master/docs/programmers_manual"
    ],
    "limitations": [
      "Moshier model range is 3000 BCE to 3000 CE; this datetime interface supports 1-3000 CE.",
      "UT1/TT accuracy depends on Swiss Ephemeris Delta T and leap-second data.",
      "Aspect orbs and eight-phase labels are explicit interpretive conventions."
    ]
  },
  "inputs": {
    "instant": "2000-01-01T12:00:00+00:00",
    "utc": "2000-01-01T12:00:00Z",
    "julian_day_tt": 2451545.0007428704,
    "julian_day_ut1": 2451545.00000411
  },
  "planets": {
    "Sun": {
      "longitude": 280.3689238651327,
      "sign": "Capricorn",
      "degrees_in_sign": 10.368923865132672,
      "speed_degrees_per_day": 1.0194320961214058,
      "retrograde": false
    },
    "Moon": {
      "longitude": 223.32382484474934,
      "sign": "Scorpio",
      "degrees_in_sign": 13.323824844749339,
      "speed_degrees_per_day": 12.021182111207215,
      "retrograde": false
    },
    "Mercury": {
      "longitude": 271.8892814035698,
      "sign": "Capricorn",
      "degrees_in_sign": 1.8892814035697825,
      "speed_degrees_per_day": 1.5562541134975347,
      "retrograde": false
    },
    "Venus": {
      "longitude": 241.56580329523328,
      "sign": "Sagittarius",
      "degrees_in_sign": 1.5658032952332803,
      "speed_degrees_per_day": 1.2090397312886196,
      "retrograde": false
    },
    "Mars": {
      "longitude": 327.96331650650734,
      "sign": "Aquarius",
      "degrees_in_sign": 27.96331650650734,
      "speed_degrees_per_day": 0.7756727755006882,
      "retrograde": false
    },
    "Jupiter": {
      "longitude": 25.25303047695292,
      "sign": "Aries",
      "degrees_in_sign": 25.25303047695292,
      "speed_degrees_per_day": 0.040761321538194305,
      "retrograde": false
    },
    "Saturn": {
      "longitude": 40.39563887401721,
      "sign": "Taurus",
      "degrees_in_sign": 10.395638874017209,
      "speed_degrees_per_day": -0.019944768921321864,
      "retrograde": true
    },
    "Uranus": {
      "longitude": 314.8092233733791,
      "sign": "Aquarius",
      "degrees_in_sign": 14.809223373379098,
      "speed_degrees_per_day": 0.05034355141125388,
      "retrograde": false
    },
    "Neptune": {
      "longitude": 303.1929813693768,
      "sign": "Aquarius",
      "degrees_in_sign": 3.1929813693768097,
      "speed_degrees_per_day": 0.035570123953115894,
      "retrograde": false
    },
    "Pluto": {
      "longitude": 251.45470899112763,
      "sign": "Sagittarius",
      "degrees_in_sign": 11.454708991127632,
      "speed_degrees_per_day": 0.03515289423055406,
      "retrograde": false
    }
  },
  "major_aspects": [
    {
      "body_1": "Sun",
      "body_2": "Moon",
      "aspect": "sextile",
      "separation": 57.04509902038333,
      "exact_angle": 60.0,
      "orb": 2.954900979616667,
      "orb_limit": 5.0
    },
    {
      "body_1": "Sun",
      "body_2": "Saturn",
      "aspect": "trine",
      "separation": 120.02671500888454,
      "exact_angle": 120.0,
      "orb": 0.026715008884536928,
      "orb_limit": 7.0
    },
    {
      "body_1": "Moon",
      "body_2": "Saturn",
      "aspect": "opposition",
      "separation": 177.07181402926787,
      "exact_angle": 180.0,
      "orb": 2.9281859707321303,
      "orb_limit": 8.0
    },
    {
      "body_1": "Moon",
      "body_2": "Uranus",
      "aspect": "square",
      "separation": 91.48539852862976,
      "exact_angle": 90.0,
      "orb": 1.4853985286297586,
      "orb_limit": 7.0
    },
    {
      "body_1": "Mercury",
      "body_2": "Mars",
      "aspect": "sextile",
      "separation": 56.07403510293756,
      "exact_angle": 60.0,
      "orb": 3.9259648970624426,
      "orb_limit": 5.0
    },
    {
      "body_1": "Mercury",
      "body_2": "Jupiter",
      "aspect": "trine",
      "separation": 113.36374907338313,
      "exact_angle": 120.0,
      "orb": 6.636250926616867,
      "orb_limit": 7.0
    },
    {
      "body_1": "Venus",
      "body_2": "Mars",
      "aspect": "square",
      "separation": 86.39751321127406,
      "exact_angle": 90.0,
      "orb": 3.6024867887259404,
      "orb_limit": 7.0
    },
    {
      "body_1": "Venus",
      "body_2": "Neptune",
      "aspect": "sextile",
      "separation": 61.62717807414353,
      "exact_angle": 60.0,
      "orb": 1.6271780741435293,
      "orb_limit": 5.0
    },
    {
      "body_1": "Mars",
      "body_2": "Jupiter",
      "aspect": "sextile",
      "separation": 57.289713970445575,
      "exact_angle": 60.0,
      "orb": 2.7102860295544247,
      "orb_limit": 5.0
    },
    {
      "body_1": "Saturn",
      "body_2": "Uranus",
      "aspect": "square",
      "separation": 85.58641550063811,
      "exact_angle": 90.0,
      "orb": 4.413584499361889,
      "orb_limit": 7.0
    },
    {
      "body_1": "Uranus",
      "body_2": "Pluto",
      "aspect": "sextile",
      "separation": 63.354514382251466,
      "exact_angle": 60.0,
      "orb": 3.354514382251466,
      "orb_limit": 5.0
    }
  ],
  "lunar_phase": {
    "angle": 302.9549009796167,
    "label": "Waning Crescent"
  }
};
