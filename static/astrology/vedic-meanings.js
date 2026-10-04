/* Local Jyotisha interpretation text. Chart facts are supplied by the caller. */
(() => {
  'use strict';

  const PLANETS = {
    Sun: 'Surya signifies illumination, vitality, authority, and the organizing center of purpose. Its condition shows how clarity and responsibility may be developed, without reducing a life to status or ego.',
    Moon: 'Chandra signifies mind, feeling, memory, receptivity, and the rhythms of everyday care. Its condition describes a changing field of response rather than a fixed personality.',
    Mercury: 'Budha signifies speech, calculation, learning, trade, and the ability to connect one fact with another. Its condition can show how discernment and communication are practiced.',
    Venus: 'Shukra signifies relationship, beauty, pleasure, agreement, and the arts of restoring value. Its condition invites reflection on what is cherished and how harmony is made workable.',
    Mars: 'Mangala signifies initiative, courage, heat, contest, and the force used to cut through obstruction. Its condition can describe how effort is directed and where restraint improves effectiveness.',
    Jupiter: 'Guru signifies counsel, learning, ethics, generosity, and the widening of perspective. Its condition can show where understanding grows through teaching, faith, and measured confidence.',
    Saturn: 'Shani signifies time, endurance, duty, consequence, and the structures built through repetition. Its condition can describe patient work and necessary limits without treating hardship as punishment.',
    Rahu: 'Rahu is the mean ascending lunar node, a calculated intersection of the Moon’s orbit with the ecliptic, not a physical planet. Jyotisha uses it to symbolize amplification, appetite, unfamiliar experience, and the pressure to distinguish fascination from understanding.',
    Ketu: 'Ketu is the mean descending lunar node opposite Rahu, not a physical planet. Jyotisha uses this calculated point to symbolize separation, inward attention, inherited skill, and the search for meaning beyond easy attachment.'
  };

  const SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];

  // Each entry is an independently authored graha-in-rashi reading.
  const RASHI_PLACEMENTS = {
    Sun: [
      'Surya in Aries puts solar clarity into decisive beginnings. Leadership grows through courage that also notices timing and consequence.',
      'Surya in Taurus steadies purpose through preservation, craft, and material continuity. Confidence develops by building value patiently without mistaking possession for security.',
      'Surya in Gemini makes inquiry and exchange central to purposeful action. A clear voice emerges when many interests are gathered into a coherent direction.',
      'Surya in Cancer links purpose with protection, memory, and belonging. Strength becomes more reliable when care includes firm emotional boundaries.',
      'Surya in Leo occupies its own rashi, favoring visible creativity and wholehearted direction. Authority works best as generous stewardship rather than a demand for recognition.',
      'Surya in Virgo expresses purpose through analysis, service, and careful improvement. The work brightens when discernment guides action without turning into relentless correction.',
      'Surya in Libra seeks a center through balance, dialogue, and shared standards. Clear commitments help cooperation retain direction when competing viewpoints arise.',
      'Surya in Scorpio concentrates will around depth, loyalty, and what is usually concealed. Purpose gains integrity through honest use of influence and a willingness to release stale control.',
      'Surya in Sagittarius directs vitality toward study, conviction, and wider horizons. Principles carry more light when enthusiasm remains answerable to experience.',
      'Surya in Capricorn gives purpose a disciplined, strategic form. Durable authority is cultivated through accountability, patience, and respect for the work behind achievement.',
      'Surya in Aquarius places identity within systems, communities, and future possibilities. Contribution becomes clearer when independence remains connected to real human needs.',
      'Surya in Pisces diffuses solar focus through imagination, compassion, and subtle perception. Purpose takes shape when inspiration is given boundaries, practice, and a concrete vessel.'
    ],
    Moon: [
      'Chandra in Aries responds quickly and seeks movement when feeling intensifies. Emotional momentum benefits from a pause that lets instinct become deliberate action.',
      'Chandra in Taurus finds steadiness through dependable rhythms, sensory ease, and tangible support. Adaptability keeps comfort restorative instead of confining.',
      'Chandra in Gemini processes experience through words, questions, and changing perspectives. Naming feelings can clarify them, provided explanation does not replace direct contact.',
      'Chandra in Cancer occupies its own rashi, emphasizing memory, nurture, and responsiveness to atmosphere. Care deepens when receptivity is paired with boundaries and regular renewal.',
      'Chandra in Leo warms the mind through creativity, loyalty, and heartfelt participation. Emotional generosity flourishes when appreciation can circulate rather than becoming a condition.',
      'Chandra in Virgo seeks calm through order, usefulness, and attentive adjustment. Practical care is strongest when imperfection is met with patience as well as skill.',
      'Chandra in Libra restores balance through companionship, beauty, and fair exchange. Inner equilibrium grows when peace-making includes an honest statement of need.',
      'Chandra in Scorpio intensifies memory and the need for trusted emotional depth. Resilience develops through truthful feeling without testing every bond for proof.',
      'Chandra in Sagittarius renews the mind through meaning, movement, and an enlarging view. Hope stays grounded when broad convictions make room for local facts.',
      'Chandra in Capricorn contains feeling within responsibility and long-range aims. Reliability can coexist with tenderness when composure is not asked to carry everything alone.',
      'Chandra in Aquarius observes emotion through patterns, ideals, and collective concerns. Belonging becomes more nourishing when intellectual distance returns to lived connection.',
      'Chandra in Pisces is highly receptive to image, mood, and unspoken currents. Rest and clear limits help compassion remain discerning rather than overwhelmed.'
    ],
    Mercury: [
      'Budha in Aries thinks through direct experiment and rapid response. Communication gains precision when speed leaves room for listening and revision.',
      'Budha in Taurus favors patient reasoning, concrete language, and knowledge tested by use. Flexibility helps established conclusions respond to new evidence.',
      'Budha in Gemini occupies its own rashi, quickening language, comparison, and exchange. Intellectual range becomes valuable when curiosity is organized around a meaningful thread.',
      'Budha in Cancer lets memory and feeling shape thought. Sensitive communication becomes clearer when intuition is checked against what was actually said and done.',
      'Budha in Leo gives speech a confident, dramatic, and creative cadence. Ideas persuade most effectively when expressive force serves the subject rather than eclipsing it.',
      'Budha in Virgo occupies its own rashi and sharpens analysis, classification, and practical craft. Discernment is most useful when it improves a process without losing the whole.',
      'Budha in Libra compares viewpoints and looks for elegant agreements. Decisions strengthen when balanced consideration eventually yields a stated position.',
      'Budha in Scorpio investigates motives, omissions, and hidden structure. Penetrating thought stays constructive when suspicion remains open to correction.',
      'Budha in Sagittarius connects facts to philosophy, teaching, and distant horizons. Big ideas gain credibility through accurate details and careful qualification.',
      'Budha in Capricorn plans communication around sequence, utility, and lasting results. Strategic thought remains alive when efficiency allows room for imagination.',
      'Budha in Aquarius examines systems, networks, and unconventional possibilities. Original ideas become usable when they are translated for the people affected by them.',
      'Budha in Pisces thinks through image, association, and subtle pattern. Intuitive perception benefits from notes, definitions, and other forms that make insight shareable.'
    ],
    Venus: [
      'Shukra in Aries approaches value and attraction with candor and initiative. Pleasure stays reciprocal when pursuit includes curiosity about the other side.',
      'Shukra in Taurus occupies its own rashi, emphasizing sensual presence, craft, and durable affection. Appreciation deepens through constancy without turning comfort into inertia.',
      'Shukra in Gemini finds beauty in wit, variety, and lively exchange. Connection becomes richer when fascination is given enough continuity to develop substance.',
      'Shukra in Cancer values tenderness, familiarity, and the making of shelter. Affection remains generous when care is offered without silent tests of loyalty.',
      'Shukra in Leo delights in warmth, artistry, and visible devotion. Generosity shines when admiration is freely exchanged rather than carefully counted.',
      'Shukra in Virgo expresses care through skill, attention, and thoughtful usefulness. Refinement supports closeness when affection is not postponed until everything is perfect.',
      'Shukra in Libra occupies its own rashi, seeking proportion, courtesy, and mutual accord. Harmony acquires depth when difficult preferences can be named gracefully.',
      'Shukra in Scorpio concentrates desire around trust, candor, and emotional depth. Intimacy grows through consent and openness rather than secrecy used as leverage.',
      'Shukra in Sagittarius values discovery, spaciousness, and shared ideals. Affection thrives when freedom includes dependable respect for promises.',
      'Shukra in Capricorn invests in commitments that mature over time. Devotion becomes visible through consistency, while tenderness keeps duty from becoming merely formal.',
      'Shukra in Aquarius values friendship, originality, and room for difference. Connection stays humane when ideals about relationship meet actual emotional presence.',
      'Shukra in Pisces heightens compassion, imagination, and longing for union. Beauty remains sustaining when empathy is joined to clear boundaries and realistic agreements.'
    ],
    Mars: [
      'Mangala in Aries occupies its own rashi, giving effort speed, courage, and a taste for direct challenges. Force becomes skillful when impulse is matched to purpose.',
      'Mangala in Taurus applies energy through persistence and sustained pressure. Progress improves when determination can change method before resistance becomes a contest of wills.',
      'Mangala in Gemini directs effort through debate, dexterity, and multiple simultaneous moves. Focus turns quick intelligence into completion rather than scattered friction.',
      'Mangala in Cancer acts protectively and may draw force from emotional allegiance. Courage matures when indirect frustration is translated into a clear request or boundary.',
      'Mangala in Leo pursues aims with pride, creativity, and dramatic confidence. Action becomes more effective when bravery includes collaboration and proportion.',
      'Mangala in Virgo channels drive into repair, technique, and precise intervention. Productive effort requires knowing when the useful correction is complete.',
      'Mangala in Libra brings force into negotiation, justice, and contested balance. Decisiveness grows by addressing conflict openly while preserving fairness.',
      'Mangala in Scorpio occupies its own rashi, concentrating effort through strategy, endurance, and depth. Power is best directed with transparency about motive and consequence.',
      'Mangala in Sagittarius acts for conviction, exploration, and an enlarging goal. Zeal becomes constructive when confidence remains teachable.',
      'Mangala in Capricorn gives disciplined structure to ambition and execution. Endurance produces strong results when achievement does not consume every reserve.',
      'Mangala in Aquarius mobilizes around systems, innovation, and collective causes. Reform gains traction when principled action stays attentive to individual effects.',
      'Mangala in Pisces moves through imagination, compassion, and shifting currents. Energy finds direction through a defined practice rather than relying on mood alone.'
    ],
    Jupiter: [
      'Guru in Aries expands through initiative, confidence, and firsthand discovery. Wisdom grows when bold belief welcomes counsel before setting direction.',
      'Guru in Taurus develops abundance through stewardship, patience, and respect for material limits. Growth stays healthy when comfort supports generosity instead of excess.',
      'Guru in Gemini multiplies questions, connections, and avenues of study. Breadth becomes wisdom when information is tested and integrated.',
      'Guru in Cancer supports learning through care, memory, and protective generosity. Nourishment expands responsibly when support builds capacity rather than dependence.',
      'Guru in Leo enlarges creativity, confidence, and the wish to guide. Teaching carries authority when warmth is matched by humility and attentive feedback.',
      'Guru in Virgo seeks understanding through method, service, and discriminating detail. Improvement gains meaning when analysis remembers the larger purpose it serves.',
      'Guru in Libra broadens perspective through dialogue, ethics, and the search for proportion. Fair judgment develops by weighing context without avoiding a decision.',
      'Guru in Scorpio pursues wisdom beneath appearances and through difficult complexity. Insight deepens when trust is earned and interpretation remains open to revision.',
      'Guru in Sagittarius occupies its own rashi, favoring philosophy, teaching, travel, and expansive conviction. Vision becomes trustworthy when principles are lived with nuance.',
      'Guru in Capricorn disciplines growth through planning, institutions, and accountable effort. Opportunity becomes durable when optimism respects sequence and constraint.',
      'Guru in Aquarius enlarges understanding through communities, systems, and future-oriented thought. Collective vision works best when abstract benefit is tested against lived experience.',
      'Guru in Pisces occupies its own rashi, deepening compassion, contemplation, and symbolic understanding. Faith becomes sustaining when openness is balanced by discernment.'
    ],
    Saturn: [
      'Shani in Aries slows immediate action long enough to test its durability. Patience and courage learn to cooperate through disciplined beginnings.',
      'Shani in Taurus builds security through conservation, repetition, and realistic valuation. Stability strengthens when necessary change is treated as maintenance rather than threat.',
      'Shani in Gemini asks thought and speech to become precise, responsible, and well structured. Confidence in communication grows through practice rather than constant self-editing.',
      'Shani in Cancer brings duty to home, care, memory, and emotional boundaries. Dependability remains humane when vulnerability is allowed a place beside obligation.',
      'Shani in Leo tests the foundations of confidence, authorship, and visible responsibility. Creative authority matures through steady craft rather than applause alone.',
      'Shani in Virgo concentrates on standards, routines, and the patient mastery of detail. Discipline is productive when it distinguishes essential care from anxious control.',
      'Shani in Libra examines fairness, commitment, and the architecture of agreement. Lasting balance is built through explicit terms and mutual accountability.',
      'Shani in Scorpio asks for endurance around trust, shared power, and concealed complexity. Restraint becomes strength when it supports honest engagement instead of guarded isolation.',
      'Shani in Sagittarius subjects beliefs, teachings, and ambitions to sustained examination. Conviction earns authority by surviving contact with evidence and difference.',
      'Shani in Capricorn occupies its own rashi, emphasizing structure, consequence, and long work. Leadership becomes durable through competent stewardship and proportionate goals.',
      'Shani in Aquarius occupies its own rashi, organizing systems, communities, and long-range reforms. Change lasts when ideals are supported by workable institutions.',
      'Shani in Pisces gives form to compassion, imagination, and spiritual discipline. Boundaries protect sensitivity while regular practice turns inspiration into service.'
    ],
    Rahu: [
      'Rahu in Aries amplifies appetite for immediacy, novelty, and self-directed action. Experiment becomes instructive when urgency is separated from genuine priority.',
      'Rahu in Taurus intensifies attention to resources, comfort, and tangible proof of value. Enoughness is easier to recognize when acquisition is measured against use.',
      'Rahu in Gemini magnifies information, networking, and the lure of the next idea. Curiosity gains depth through source-checking and sustained attention.',
      'Rahu in Cancer heightens concern with belonging, protection, and emotional recognition. Care becomes clearer when inherited needs are distinguished from present conditions.',
      'Rahu in Leo enlarges the pull of visibility, creativity, and singular importance. Original expression matures when attention serves the work rather than directing it.',
      'Rahu in Virgo intensifies optimization, technique, and the search for a decisive fix. Discernment improves when uncertainty is tolerated alongside careful analysis.',
      'Rahu in Libra magnifies fascination with alliance, approval, and social balance. Partnership becomes more lucid when agreement does not obscure individual responsibility.',
      'Rahu in Scorpio draws attention toward secrets, intensity, and transformative knowledge. Investigation stays grounded when depth is not confused with danger or control.',
      'Rahu in Sagittarius amplifies the pursuit of certainty, expertise, and distant horizons. Expansive claims benefit from humility, context, and verifiable particulars.',
      'Rahu in Capricorn magnifies ambition, systems of rank, and measurable accomplishment. Strategy remains meaningful when success is defined beyond recognition alone.',
      'Rahu in Aquarius intensifies identification with innovation, networks, and collective futures. New systems deserve testing for whom they include and how they work in practice.',
      'Rahu in Pisces enlarges imagination, transcendence, and attraction to what resists definition. Inspiration remains navigable through evidence, boundaries, and ordinary routines.'
    ],
    Ketu: [
      'Ketu in Aries can detach action from the need for applause, leaving a spare instinct for decisive movement. Reflection helps distinguish clean initiative from automatic withdrawal.',
      'Ketu in Taurus can loosen attachment to familiar measures of comfort and worth. Simplicity becomes meaningful when material responsibilities still receive care.',
      'Ketu in Gemini can turn a practiced mind away from surface explanation toward silence or underlying pattern. Communication stays connected by making implicit knowledge explicit.',
      'Ketu in Cancer can make belonging and memory feel inward, private, or difficult to name. Gentle attention helps inherited emotional habits become conscious resources.',
      'Ketu in Leo can separate creativity from ordinary recognition, sharpening the question of why expression matters. Warm participation keeps self-sufficiency from becoming distance.',
      'Ketu in Virgo can bring instinctive skill with detail alongside disinterest in conventional perfection. Practical service gains coherence when intuition is documented and shared.',
      'Ketu in Libra can expose the limits of approval and formal harmony. Relationships deepen when detachment supports honest presence rather than avoidance.',
      'Ketu in Scorpio can confer familiarity with hidden processes and abrupt inner change. Insight remains integrative when intensity is followed by patient reconstruction.',
      'Ketu in Sagittarius can turn inherited belief into a search beyond slogans and settled doctrine. Wisdom expands when private conviction remains in conversation with evidence.',
      'Ketu in Capricorn can reduce the appeal of rank while preserving an instinct for structure. Duty becomes purposeful when achievement is connected to an inwardly chosen standard.',
      'Ketu in Aquarius can create distance from group identity even while revealing systemic patterns. Contribution becomes grounded by returning from abstraction to particular people.',
      'Ketu in Pisces can deepen contemplative sensitivity and loosen ordinary categories. Clear routines help subtle awareness remain embodied and communicable.'
    ]
  };

  const HOUSES = {
    1: 'The first bhava concerns embodiment, orientation, presence, and the manner of entering experience. A graha here becomes prominent in how initiative and self-direction are developed.',
    2: 'The second bhava concerns speech, stored resources, family continuity, and what sustains daily life. A graha here brings its themes to stewardship, values, and the use of what is held.',
    3: 'The third bhava concerns effort, skill, communication, siblings, and nearby movement. A graha here works through practice, initiative, and repeated acts of learning.',
    4: 'The fourth bhava concerns home, inner steadiness, care, land, and foundational belonging. A graha here colors the work of establishing shelter and emotional ground.',
    5: 'The fifth bhava concerns learning, counsel, creativity, play, and the fruits of attentive intelligence. A graha here contributes its themes to expression and considered judgment.',
    6: 'The sixth bhava concerns service, conflict, obligations, health routines, and problems requiring method. A graha here is developed through practical response and sustainable discipline.',
    7: 'The seventh bhava concerns agreements, partnership, exchange, and direct encounter with others. A graha here becomes visible in reciprocity, negotiation, and shared terms.',
    8: 'The eighth bhava concerns shared resources, vulnerability, uncertainty, inheritance, and deep reorganization. A graha here asks for careful engagement with what cannot be controlled alone.',
    9: 'The ninth bhava concerns teachers, ethics, pilgrimage, higher learning, and the principles that orient a life. A graha here shapes the search for context, guidance, and a wider view.',
    10: 'The tenth bhava concerns action in the world, responsibility, vocation, and visible contribution. A graha here brings its themes into work, accountability, and public consequence.',
    11: 'The eleventh bhava concerns gains, allies, networks, and aims pursued with others. A graha here influences how support is exchanged and longer-range hopes are organized.',
    12: 'The twelfth bhava concerns retreat, expenditure, solitude, distant places, and release. A graha here invites attention to endings, restoration, and what works outside ordinary visibility.'
  };

  const NAKSHATRAS = [
    ['Ashwini', 'Ketu', 'the Ashvins and swift arrival', 'Ashwini carries the image of the divine horsemen, associated with quick response, movement, and restoration. It invites initiative that remains attentive enough to help rather than merely hurry.'],
    ['Bharani', 'Venus', 'Yama and the act of bearing', 'Bharani is linked with Yama, restraint, and the capacity to carry what has been entrusted. Its symbolism asks how desire can coexist with limits, integrity, and responsible containment.'],
    ['Krittika', 'Sun', 'Agni and the cutting flame', 'Krittika is associated with Agni, whose flame separates, clarifies, and transforms. Its edge can support decisive refinement when criticism serves illumination rather than injury.'],
    ['Rohini', 'Moon', 'Prajapati and fertile growth', 'Rohini evokes growth, beauty, and the generative ordering of form under Prajapati. It favors patient cultivation while asking that attachment not close around what is flourishing.'],
    ['Mrigashira', 'Mars', 'Soma and the searching deer', 'Mrigashira joins Soma with the image of a deer’s searching head. Curiosity and gentle pursuit are emphasized, with value in knowing when a promising trail needs verification.'],
    ['Ardra', 'Rahu', 'Rudra and the gathering storm', 'Ardra is associated with Rudra and the intensity of a storm that exposes what is tender. It can symbolize honest release and fierce inquiry followed by the work of reorientation.'],
    ['Punarvasu', 'Jupiter', 'Aditi and return to spaciousness', 'Punarvasu is linked with Aditi, boundlessness, and the return of light after difficulty. Its rhythm supports renewal through simplicity, perspective, and a return to first principles.'],
    ['Pushya', 'Saturn', 'Brihaspati and nourishment', 'Pushya is associated with Brihaspati and with nourishment that helps something worthy mature. It favors teaching, care, and disciplined support while keeping guidance proportionate.'],
    ['Ashlesha', 'Mercury', 'the Nagas and entwining power', 'Ashlesha is linked with the Nagas and the intelligence of binding, coiling, and close perception. It asks for discernment about persuasion, secrecy, and the ties that both protect and constrain.'],
    ['Magha', 'Ketu', 'the Pitris and ancestral seat', 'Magha is associated with the Pitris, ancestral continuity, and the dignity of an inherited seat. Its symbolism invites respect for lineage alongside conscious choice about which legacies to carry forward.'],
    ['Purva Phalguni', 'Venus', 'Bhaga and restorative enjoyment', 'Purva Phalguni is linked with Bhaga, delight, sharing, and the ease that allows creativity to open. Pleasure becomes renewing when hospitality and enjoyment remain reciprocal.'],
    ['Uttara Phalguni', 'Sun', 'Aryaman and sustaining agreements', 'Uttara Phalguni is associated with Aryaman, alliance, patronage, and the obligations that sustain friendship. It favors clear commitments whose generosity can endure beyond the first enthusiasm.'],
    ['Hasta', 'Moon', 'Savitar and the skillful hand', 'Hasta is linked with Savitar and the hand that grasps, shapes, blesses, and releases. Its symbolism supports practical skill when control remains responsive to the material at hand.'],
    ['Chitra', 'Mars', 'Tvashtar and brilliant form', 'Chitra is associated with Tvashtar, the celestial artisan, and with striking form made through craft. It invites beauty that reveals structure rather than decoration used to conceal it.'],
    ['Swati', 'Rahu', 'Vayu and independent movement', 'Swati is linked with Vayu, wind, motion, and the freedom to find an independent course. Flexibility becomes strength when movement also develops direction and rootedness.'],
    ['Vishakha', 'Jupiter', 'Indra-Agni and a branching aim', 'Vishakha is associated with Indra and Agni, combining directed power with transformative fire. Its branching image emphasizes chosen aims and the need to examine what ambition is feeding.'],
    ['Anuradha', 'Saturn', 'Mitra and devoted friendship', 'Anuradha is linked with Mitra, friendship, accord, and loyalty formed through shared order. Devotion grows through reliable participation while allowing bonds enough space to breathe.'],
    ['Jyeshtha', 'Mercury', 'Indra and senior responsibility', 'Jyeshtha is associated with Indra and the burdens of precedence, protection, and earned authority. Its symbolism asks that capability be used for stewardship rather than superiority.'],
    ['Mula', 'Ketu', 'Nirriti and the root', 'Mula is linked with Nirriti and the act of going to the root of a matter. Investigation can clear unstable foundations when it is followed by integration rather than endless undoing.'],
    ['Purva Ashadha', 'Venus', 'the Apas and cleansing waters', 'Purva Ashadha is associated with the Waters and their cleansing, enlivening movement. It supports conviction and renewal while inviting openness to what the current can teach.'],
    ['Uttara Ashadha', 'Sun', 'the Vishvadevas and enduring principles', 'Uttara Ashadha is linked with the Vishvadevas, a collective of universal principles. Its symbolism favors lasting achievement grounded in shared ethics rather than victory at any cost.'],
    ['Shravana', 'Moon', 'Vishnu and attentive hearing', 'Shravana is associated with Vishnu and the attentive hearing through which knowledge travels. Listening, learning, and connecting distant steps are emphasized over assuming the whole story is already known.'],
    ['Dhanishta', 'Mars', 'the Vasus and resonant abundance', 'Dhanishta is linked with the Vasus and with rhythm, resonance, and resources that circulate. Prosperity is framed as coordinated participation and good timing rather than accumulation alone.'],
    ['Shatabhisha', 'Rahu', 'Varuna and the enclosing circle', 'Shatabhisha is associated with Varuna, hidden order, and the encompassing circle. It invites independent inquiry, privacy, and repair while cautioning against isolation disguised as objectivity.'],
    ['Purva Bhadrapada', 'Jupiter', 'Aja Ekapada and concentrated fire', 'Purva Bhadrapada is linked with Aja Ekapada and an intense, one-pointed orientation. Its symbolism can focus ideals sharply, making moderation and practical accountability essential companions.'],
    ['Uttara Bhadrapada', 'Saturn', 'Ahir Budhnya and the depth below', 'Uttara Bhadrapada is associated with Ahir Budhnya, the serpent of the deep, and with quiet foundations. It favors patient inner stability that can hold complexity without becoming inert.'],
    ['Revati', 'Mercury', 'Pushan and safe passage', 'Revati is linked with Pushan, nourishment, guidance, and protection along the road. Its closing place in the cycle emphasizes completion, humane direction, and preparation for a new journey.']
  ].map(([name, lord, symbolism, text], index) => Object.freeze({name, index: index + 1, lord, symbolism, text}));

  const ASPECT_DISTANCES = {
    Sun: [7], Moon: [7], Mercury: [7], Venus: [7], Mars: [4, 7, 8],
    Jupiter: [5, 7, 9], Saturn: [3, 7, 10], Rahu: [], Ketu: []
  };

  const ASPECT_ACTIONS = {
    Sun: 'directs clarity, purpose, and accountable visibility toward',
    Moon: 'directs attention, response, and the need for steadiness toward',
    Mercury: 'directs inquiry, speech, and discriminating thought toward',
    Venus: 'directs valuation, accord, and the wish to harmonize toward',
    Mars: 'directs effort, heat, and decisive pressure toward',
    Jupiter: 'directs counsel, confidence, and an enlarging perspective toward',
    Saturn: 'directs discipline, delay, and structural scrutiny toward',
    Rahu: 'directs amplification, appetite, and unfamiliar perspective toward',
    Ketu: 'directs detachment, concentration, and inward discrimination toward'
  };

  const keyFor = (value, collection) => {
    const wanted = String(value == null ? '' : value).trim().toLowerCase();
    return Object.keys(collection).find(key => key.toLowerCase() === wanted) || null;
  };
  const isNatal = kind => String(kind || '').trim().toLowerCase() === 'natal';
  const validHouse = value => {
    if (value === null || value === undefined || value === '') return null;
    const number = Number(value);
    return Number.isInteger(number) && number >= 1 && number <= 12 ? number : null;
  };
  const ordinal = number => `${number}${number === 1 ? 'st' : number === 2 ? 'nd' : number === 3 ? 'rd' : 'th'}`;

  function planet(name) {
    const key = keyFor(name, PLANETS);
    return key ? PLANETS[key] : 'This graha is not included in the local Vedic meanings guide.';
  }

  function placement(name, placementData, kind) {
    const planetName = keyFor(name, PLANETS);
    const data = placementData && typeof placementData === 'object' ? placementData : {};
    const signName = SIGNS.find(sign => sign.toLowerCase() === String(data.sign || '').trim().toLowerCase());
    if (!planetName || !signName) {
      return [{title: 'Vedic placement', text: 'This placement is not included in the local Vedic meanings guide.'}];
    }

    const sections = [{
      title: `${planetName} in ${signName}`,
      text: isNatal(kind)
        ? RASHI_PLACEMENTS[planetName][SIGNS.indexOf(signName)]
        : `In the current sidereal sky, ${RASHI_PLACEMENTS[planetName][SIGNS.indexOf(signName)]}`
    }];

    const house = validHouse(data.whole_sign_house);
    if (isNatal(kind) && house) {
      sections.push({title: `${planetName} in the ${ordinal(house)} bhava`, text: HOUSES[house]});
    }

    const nakshatraData = data.nakshatra && typeof data.nakshatra === 'object' ? data.nakshatra : null;
    if (nakshatraData) {
      const byIndex = Number.isInteger(Number(nakshatraData.index)) ? NAKSHATRAS[Number(nakshatraData.index) - 1] : null;
      const byName = NAKSHATRAS.find(item => item.name.toLowerCase() === String(nakshatraData.name || '').trim().toLowerCase());
      const star = byName || byIndex;
      const pada = Number(nakshatraData.pada);
      if (star && Number.isInteger(pada) && pada >= 1 && pada <= 4) {
        const reportedLord = keyFor(nakshatraData.lord, PLANETS);
        const lord = reportedLord || star.lord;
        sections.push({
          title: `${star.name}, pada ${pada}`,
          text: `${star.text} Pada ${pada} is the ${ordinal(pada)} quarter of this nakshatra and locates the placement within the star’s span. Its traditional planetary ruler is ${lord}.`
        });
      }
    }
    return sections;
  }

  function retrograde(name, kind) {
    const planetName = keyFor(name, PLANETS);
    if (!planetName) return 'This graha is not included in the local Vedic meanings guide.';
    if (planetName === 'Rahu' || planetName === 'Ketu') {
      return `${planetName} is a mean lunar node, not a physical planet. Its backward movement is the continuous convention of the mean-node calculation, so it is not interpreted as a planet turning retrograde or stationing.`;
    }
    if (planetName === 'Sun' || planetName === 'Moon') {
      return `${planetName} is not read as retrograde in this chart model.`;
    }
    const context = isNatal(kind) ? 'in a natal chart' : 'in the current sky';
    return `${planetName} retrograde ${context} is an apparent reversal traditionally used to revisit and internalize this graha’s themes. It suggests review and altered pacing, not inevitable delay or failure.`;
  }

  function aspect(body1, body2, aspectName, kind, houseDistance) {
    const source = keyFor(body1, PLANETS);
    const target = keyFor(body2, PLANETS);
    const distance = Number(houseDistance);
    const label = String(aspectName || '').trim().toLowerCase();
    if (!source || !target || !Number.isInteger(distance) || !ASPECT_DISTANCES[source].includes(distance)
        || !['full', 'graha drishti', 'drishti', 'aspect'].includes(label)) {
      return 'This graha drishti is not included in the local Vedic meanings guide.';
    }
    const rule = distance === 7
      ? 'the full seventh-place glance shared by the grahas'
      : `the full ${ordinal(distance)}-place special glance of ${source}`;
    const setting = isNatal(kind) ? 'Within the natal chart' : 'In the current sidereal sky';
    return `${setting}, ${source} casts ${rule} toward ${target}. From ${source}, this directional drishti ${ASPECT_ACTIONS[source]} ${target}’s themes; it is counted sign by sign in the Jyotisha graha-drishti framework.`;
  }

  for (const passages of Object.values(RASHI_PLACEMENTS)) Object.freeze(passages);
  Object.freeze(RASHI_PLACEMENTS);
  Object.freeze(PLANETS);
  Object.freeze(HOUSES);
  Object.freeze(NAKSHATRAS);
  for (const distances of Object.values(ASPECT_DISTANCES)) Object.freeze(distances);
  Object.freeze(ASPECT_DISTANCES);

  window.VedicMeanings = Object.freeze({
    planet, placement, retrograde, aspect,
    tables: Object.freeze({planets: PLANETS, signs: Object.freeze([...SIGNS]), rashis: RASHI_PLACEMENTS, houses: HOUSES, nakshatras: NAKSHATRAS})
  });
})();
