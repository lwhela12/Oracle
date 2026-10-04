(() => {
  'use strict';
  const chart = window.ORACLE_SKY_STUDY;
  const glyphs = { Sun:'☉', Moon:'☽', Mercury:'☿', Venus:'♀', Mars:'♂', Jupiter:'♃', Saturn:'♄', Uranus:'♅', Neptune:'♆', Pluto:'♇' };
  const primary = document.querySelector('#form-chart');
  const pause = document.querySelector('#pause');
  const phaseText = document.querySelector('#phase');
  const list = document.querySelector('#planet-list');
  let revealed = false;
  let paused = false;
  let selected = null;
  const position = p => {
    const minutes = Math.floor(p.degrees_in_sign * 60);
    return `${Math.floor(minutes / 60)}° ${String(minutes % 60).padStart(2,'0')}′ ${p.sign}`;
  };
  const field = new CelestialField(document.querySelector('#sky'), chart, {
    onPhase(phase) {
      document.body.classList.toggle('resolved', phase === 'resolved');
      revealed = phase !== 'drifting';
      phaseText.textContent = { drifting:'A field of possibility', gathering:'Gathering around the planets', resolved:'The moment takes shape' }[phase];
      primary.replaceChildren(document.createTextNode(revealed ? 'Release the stars' : 'Form the chart'));
      const arrow = document.createElement('span');
      arrow.textContent = revealed ? '↺' : '↗'; arrow.setAttribute('aria-hidden','true');
      primary.append(arrow);
    }
  });
  primary.addEventListener('click', () => { if (revealed) field.disperse(); else field.reveal(); });
  pause.addEventListener('click', () => {
    paused = !paused; field.setPaused(paused);
    pause.setAttribute('aria-pressed', String(paused));
    pause.textContent = paused ? 'Resume motion' : 'Pause motion';
  });
  for (const [name, planet] of Object.entries(chart.planets)) {
    const button = document.createElement('button');
    button.className = 'planet'; button.setAttribute('aria-pressed','false');
    button.setAttribute('aria-label', `${name}, ${position(planet)}${planet.retrograde ? ', retrograde' : ''}`);
    for (const [className, text] of [['glyph',glyphs[name]],['name',name],['position',position(planet)],['motion',planet.retrograde ? 'RETROGRADE' : '']]) {
      const span = document.createElement('span'); span.className = className; span.textContent = text;
      if (className === 'glyph') span.setAttribute('aria-hidden','true');
      button.append(span);
    }
    button.addEventListener('click', () => {
      selected = selected === name ? null : name;
      for (const other of list.children) other.setAttribute('aria-pressed', String(other === button && selected !== null));
      field.selectPlanet(selected);
      if (selected && !revealed) field.reveal();
      document.querySelector('#selection-label').textContent = selected ? `${name.toUpperCase()} · ${planet.retrograde ? 'RETROGRADE' : 'DIRECT'}` : 'THE SKY AT A GLANCE';
      document.querySelector('#selection-title').textContent = selected ? position(planet) : 'Waning crescent';
      const aspects = chart.major_aspects.filter(a => a.body_1 === name || a.body_2 === name);
      document.querySelector('#selection-copy').textContent = selected
        ? (aspects.length ? aspects.slice(0,3).map(a => `${a.aspect[0].toUpperCase()+a.aspect.slice(1)} ${a.body_1 === name ? a.body_2 : a.body_1} · ${a.orb.toFixed(1)}° orb`).join(' / ') : 'No major aspects within the chart’s configured orbs.')
        : 'Ten celestial bodies, one shared sky. Form the chart, then choose a planet to explore its position.';
    });
    list.append(button);
  }
  window.addEventListener('pagehide', () => field.destroy(), {once:true});
})();
