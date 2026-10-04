/* Instant, local astrology meanings. Chart facts are supplied by the caller. */
(() => {
  'use strict';

  const planets = {
    Sun: {
      function: 'identity, vitality, and the wish to live from a coherent center',
      meaning: 'The Sun symbolizes identity, vitality, purpose, and the part of life that seeks a clear center. Its placement is traditionally read as a path toward fuller self-expression, rather than a complete description of a person.'
    },
    Moon: {
      function: 'feeling, instinct, memory, and the need for emotional shelter',
      meaning: 'The Moon symbolizes feeling, instinct, memory, habit, and the rhythms that restore a sense of safety. Its placement is traditionally read as an emotional climate and a pattern of response, not a fixed verdict about temperament.'
    },
    Mercury: {
      function: 'thought, language, perception, and exchange',
      meaning: 'Mercury symbolizes thought, language, curiosity, learning, and exchange. Its placement describes the style through which information may be gathered and expressed, while leaving room for many ways of thinking and communicating.'
    },
    Venus: {
      function: 'attraction, relationship, pleasure, and value',
      meaning: 'Venus symbolizes attraction, affection, aesthetics, pleasure, and the values that guide connection. Its placement is often used to reflect on what invites harmony and appreciation, without defining whom or how anyone must love.'
    },
    Mars: {
      function: 'initiative, desire, courage, and the use of force',
      meaning: 'Mars symbolizes initiative, desire, courage, anger, and the way energy is directed. Its placement can suggest a style of taking action and meeting friction; it does not determine conduct or justify impulsive choices.'
    },
    Jupiter: {
      function: 'growth, faith, perspective, and the search for meaning',
      meaning: 'Jupiter symbolizes growth, confidence, generosity, perspective, and the search for meaning. Its placement is traditionally associated with places where experience may broaden, while excess can arise when possibility outruns proportion.'
    },
    Saturn: {
      function: 'structure, limits, responsibility, and durable mastery',
      meaning: 'Saturn symbolizes structure, limits, responsibility, time, and the patience required for durable mastery. Its placement can point toward serious work and earned authority, rather than punishment or an unavoidable burden.'
    },
    Uranus: {
      function: 'awakening, independence, disruption, and invention',
      meaning: 'Uranus symbolizes awakening, independence, invention, and breaks with established patterns. Its placement is often read as a field of experimentation and change, where freedom works best when it remains conscious of consequences.'
    },
    Neptune: {
      function: 'imagination, compassion, longing, and the dissolving of boundaries',
      meaning: 'Neptune symbolizes imagination, compassion, spirituality, longing, and the dissolving of boundaries. Its placement can invite sensitivity and vision, alongside a need to distinguish inspiration from projection or escape.'
    },
    Pluto: {
      function: 'depth, power, endings, and profound renewal',
      meaning: 'Pluto symbolizes depth, power, compulsion, endings, and profound renewal. Its placement is traditionally used to explore slow processes of release and regeneration, without implying that crisis or loss is fated.'
    }
  };

  const signs = {
    Aries: {
      style: 'direct, initiating, and willing to meet experience head-on',
      invitation: 'begin with courage while making room for timing and response'
    },
    Taurus: {
      style: 'steady, embodied, and attentive to what can be sustained',
      invitation: 'build patiently while noticing when security has become resistance'
    },
    Gemini: {
      style: 'curious, adaptable, and alive to multiple points of view',
      invitation: 'follow the useful question while giving scattered impressions a clear thread'
    },
    Cancer: {
      style: 'protective, receptive, and guided by memory and belonging',
      invitation: 'honor sensitivity while distinguishing care from defensiveness'
    },
    Leo: {
      style: 'expressive, warm, and drawn toward wholehearted participation',
      invitation: 'create generously while letting recognition be a response rather than the only aim'
    },
    Virgo: {
      style: 'discerning, practical, and concerned with useful refinement',
      invitation: 'improve what is within reach without demanding perfection first'
    },
    Libra: {
      style: 'relational, balancing, and attentive to proportion and fairness',
      invitation: 'seek mutuality while keeping a clear relationship to your own position'
    },
    Scorpio: {
      style: 'intense, private, and willing to engage what lies beneath the surface',
      invitation: 'meet complexity honestly while loosening the need to control every outcome'
    },
    Sagittarius: {
      style: 'expansive, candid, and oriented toward meaning and discovery',
      invitation: 'follow the larger horizon while staying accountable to the details underfoot'
    },
    Capricorn: {
      style: 'disciplined, strategic, and aware of time, consequence, and responsibility',
      invitation: 'choose the durable path while allowing ambition to remain human'
    },
    Aquarius: {
      style: 'independent, future-minded, and responsive to systems and collective patterns',
      invitation: 'make space for the new while staying connected to lived feeling'
    },
    Pisces: {
      style: 'imaginative, permeable, and responsive to subtle emotional currents',
      invitation: 'welcome intuition while giving it enough form and boundary to be useful'
    }
  };

  const houses = {
    1: 'self-presentation, approach, and the way one enters experience',
    2: 'resources, values, livelihood, and the ground of self-worth',
    3: 'learning, language, siblings, neighbors, and everyday exchange',
    4: 'home, roots, family patterns, and private foundations',
    5: 'creativity, play, romance, pleasure, and personal expression',
    6: 'daily work, craft, health routines, and practical service',
    7: 'partnership, agreements, close encounter, and mutual reflection',
    8: 'shared resources, intimacy, trust, loss, and transformation',
    9: 'higher learning, travel, belief, publishing, and wider horizons',
    10: 'vocation, public life, reputation, and long-range contribution',
    11: 'friendship, community, collaboration, and hopes for the future',
    12: 'retreat, inner life, hidden patterns, compassion, and release'
  };

  const aspectNames = ['conjunction', 'sextile', 'square', 'trine', 'opposition'];
  const aspectLibrary = window.AstrologyAspectLibrary || {};
  for (const entry of Object.values(aspectLibrary)) Object.freeze(entry);
  Object.freeze(aspectLibrary);

  const retrogrades = {
    Mercury: 'reviewing messages, plans, assumptions, and unfinished conversations',
    Venus: 'reconsidering values, attractions, agreements, and the terms of reciprocity',
    Mars: 'redirecting effort, revisiting motives, and learning where force is poorly spent',
    Jupiter: 'turning growth inward to examine belief, judgment, and the meaning assigned to experience',
    Saturn: 'reviewing commitments, boundaries, authority, and structures that need reinforcement or revision',
    Uranus: 'internalizing the pressure for change and reconsidering what freedom requires',
    Neptune: 'revisiting ideals, sensitivities, and places where imagination needs clearer boundaries',
    Pluto: 'deepening a long process of confronting power, release, and regeneration'
  };

  const keyFor = (value, collection) => {
    const wanted = String(value == null ? '' : value).trim().toLowerCase();
    return Object.keys(collection).find(key => key.toLowerCase() === wanted) || null;
  };

  const isNatal = chartKind => String(chartKind || '').trim().toLowerCase() === 'natal';

  const validHouse = value => {
    if (value === null || value === undefined || value === '') return null;
    const number = Number(value);
    return Number.isInteger(number) && number >= 1 && number <= 12 ? number : null;
  };

  function planet(name) {
    const key = keyFor(name, planets);
    return key ? planets[key].meaning : 'This celestial body is not included in the built-in meanings guide.';
  }

  function placement(name, sign, house, chartKind) {
    const planetName = keyFor(name, planets);
    const signName = keyFor(sign, signs);
    const houseNumber = validHouse(house);

    if (!planetName || !signName) {
      return [{
        title: 'Placement',
        text: 'This placement is not included in the built-in meanings guide.'
      }];
    }

    const body = planets[planetName];
    const zodiac = signs[signName];
    const sections = [];
    if (isNatal(chartKind)) {
      sections.push({
        title: `${planetName} in ${signName}`,
        text: `${planetName} in ${signName} brings ${body.function} into a style that is ${zodiac.style}. In a natal chart, this can be explored as an invitation to ${zodiac.invitation}.`
      });
      if (houseNumber) {
        sections.push({
          title: `${planetName} in the ${ordinalWord(houseNumber)} house`,
          text: `The ${ordinalWord(houseNumber)} house concerns ${houses[houseNumber]}. With ${planetName} here, ${body.function} may become an especially meaningful part of how this area of life is experienced and developed.`
        });
      }
    } else {
      sections.push({
        title: `${planetName} in ${signName}`,
        text: `${planetName} moving through ${signName} brings the present sky's emphasis on ${body.function} into a mode that is ${zodiac.style}. This shared pattern favors reflection on how to ${zodiac.invitation}.`
      });
      if (houseNumber) {
        sections.push({
          title: `${planetName} in the ${ordinalWord(houseNumber)} house`,
          text: `From the selected location, ${planetName} is moving through the ${ordinalWord(houseNumber)} house, bringing the local sky's attention to ${houses[houseNumber]}.`
        });
      }
    }
    return sections;
  }

  function aspect(body1, body2, type, chartKind) {
    const firstName = keyFor(body1, planets);
    const secondName = keyFor(body2, planets);
    const aspectName = String(type || '').trim().toLowerCase();
    if (!firstName || !secondName || !aspectNames.includes(aspectName)) {
      return 'This aspect is not included in the built-in meanings guide.';
    }
    // Within one chart a body cannot aspect itself; those essays are transit-only.
    if (firstName === secondName && chartKind !== 'transit') {
      return 'A planet’s connection to its own birth-chart position belongs to a transit reading.';
    }
    const order = Object.keys(planets);
    const pair = [firstName, secondName].sort((a, b) => order.indexOf(a) - order.indexOf(b)).join('|');
    return aspectLibrary[pair]?.[aspectName]
      || 'An explanation for this connection is not available yet.';
  }

  function retrograde(name, chartKind) {
    const planetName = keyFor(name, planets);
    if (!planetName) return 'This celestial body is not included in the built-in meanings guide.';
    if (planetName === 'Sun' || planetName === 'Moon') {
      return `${planetName} is not interpreted as retrograde; the Sun and Moon do not enter apparent retrograde motion in this chart model.`;
    }
    const theme = retrogrades[planetName];
    if (isNatal(chartKind)) {
      return `${planetName} retrograde in a natal chart is traditionally read as a more inward, recursive expression of ${planets[planetName].function}. It may invite ${theme}, without implying deficiency or a fixed life story.`;
    }
    return `${planetName} is retrograde in the current sky, an apparent reversal traditionally associated with ${theme}. This is a period-style symbol for reflection and revision, not a prediction that events must reverse or go wrong.`;
  }

  function ordinalWord(number) {
    return ['first', 'second', 'third', 'fourth', 'fifth', 'sixth',
      'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth'][number - 1];
  }

  window.AstrologyMeanings = Object.freeze({planet, placement, aspect, retrograde});
})();
