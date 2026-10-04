/* Chart facts come from the server. Only an explicit Save writes personal data. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const glyphs = {Sun:'☉', Moon:'☽', Mercury:'☿', Venus:'♀', Mars:'♂', Jupiter:'♃', Saturn:'♄', Uranus:'♅', Neptune:'♆', Pluto:'♇', Rahu:'☊', Ketu:'☋'};
  const kindNames={natal:'Birth chart',current:'Sky Now',transit:'Personal transits',horoscope:'Daily horoscope'};
  const westernBodies=['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn','Uranus','Neptune','Pluto'];
  const vedicBodies=['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn','Rahu','Ketu'];
  const isVedic=chart=>chart?.tradition==='vedic';
  const horoscopeSign=chart=>chart.horoscope?.moon_sign || chart.horoscope?.sun_sign;
  const ordinal=n=>`${n}${n===1 ? 'st' : n===2 ? 'nd' : n===3 ? 'rd' : 'th'}`;
  const nakshatraLabel=n=>`${n.name} · Pada ${n.pada}`;
  const entryKinds = ['natal','horoscope'];
  const journalKey = 'oracle_astrology_journal_v1';
  let kind = 'natal', place = null, field, selected = null, activeAspect = null, paused = false;
  let siderealLabel = 'Lahiri';
  const ayanamsaLabel = chart => chart.ayanamsa?.convention_id==='iae-2021' ? 'IAE 2021' : 'Lahiri';
  let dateBounds = {min:'0001-01-01',max:'3000-12-31'};
  let record = null, controller = null, revision = 0, searchController = null, searchRevision = 0;
  let pdfWorker = null, searchTimer = null;
  const phaseLabels = {drifting:'A field of possibility', gathering:'Gathering around the planets', resolved:'The moment takes shape'};
  const clone = value => JSON.parse(JSON.stringify(value));
  const position = value => {
    const minute = Math.floor(Number(value.degrees_in_sign) * 60);
    return `${Math.floor(minute / 60)}° ${String(minute % 60).padStart(2,'0')}′ ${value.sign}`;
  };
  function text(id, value) { $(id).textContent = value; }
  function message(id, value) { text(id,value); $(id).hidden = !value; }
  function createField(chart = {planets:{}}) {
    if (field) field.destroy();
    document.body.classList.remove('resolved');
    field = new CelestialField($('sky'),chart,{nodeLayer:$('planet-nodes'),onSelect(name) {
      selectPlanet(selected === name ? null : name);
    },onPhase(phase) {
      document.body.classList.toggle('resolved',phase === 'resolved');
      text('phase',phaseLabels[phase]);
    },onRevealProgress(progress) {
      // Finish the backdrop ahead of the symbols, using the same pausable clock.
      const fade = Math.min(1,progress / 0.65);
      document.body.style.setProperty('--reveal-progress',String(fade * fade * (3 - 2 * fade)));
    }});
    field.setPaused(paused);
  }
  function setKind(next) {
    next=entryKinds.includes(next) ? next : 'natal';
    kind=next;
    for(const name of entryKinds) $('kind-'+name).setAttribute('aria-pressed',String(next===name));
    $('birth-fields').hidden=false; $('birth-fields').disabled=false;
    updateBirthRequirements();
    const vedic=$('tradition').value==='vedic';
    $('horoscope-fields').hidden=next!=='horoscope' || vedic; $('horoscope-fields').disabled=next!=='horoscope' || vedic;
    text('tradition-help',vedic ? 'Sidereal zodiac · '+siderealLabel : 'Tropical zodiac');
    text('horoscope-tagline',vedic ? 'Today for your Moon sign' : 'Today for your Sun sign');
    $('place-fields').hidden=false;
    text('privacy-copy',next==='horoscope' ? `Save keeps your birth details and reading in this browser. Gemini receives your ${vedic ? 'Moon sign, birth nakshatra' : 'Sun sign'} and today’s chart.` : 'Save stores your chart inputs and reading in this browser. Interpretation sends chart placements to Gemini.');
    const descriptions={natal:'Your birth date, recorded time and birthplace reveal your personal chart.',horoscope:vedic ? 'Your birth Moon guides a Vedic reading of today’s sky.' : 'Your birth details guide a general Sun-sign reading of today’s sky.'};
    text('kind-description',descriptions[next]);
    $('generate').firstChild.textContent={natal:'Reveal your birth chart ',horoscope:'Read my horoscope '}[next];
    resetFold(); message('form-error','');
  }
  function updateBirthRequirements() {
    const required=kind==='natal' || $('tradition').value==='vedic';
    $('birth-time').required=required;
    $('place-query').required=required;
    $('birth-date').min=dateBounds.min;
    $('birth-date').max=kind==='horoscope' ? [new Date().toISOString().slice(0,10),dateBounds.max].sort()[0] : dateBounds.max;
    text('birth-time-label','Local birth time'+(required ? '' : ' (optional)'));
    text('place-label','Birthplace'+(required ? '' : ' (optional)'));
    text('birth-details-help',required
      ? (kind==='horoscope' ? 'Your birth date, recorded time and birthplace are required to calculate your Vedic Moon sign and birth nakshatra.' : 'Use the recorded local time. An unknown birth time cannot give reliable houses or a rising sign.')
      : 'Add both time and birthplace to calculate your Sun sign from your birth moment. Without both, we use approximate birthday ranges. This remains a general daily horoscope.');
  }
  $('tradition').addEventListener('change',()=>setKind(kind));
  async function applyCapabilities() {
    try {
      const response=await fetch('/astrology/capabilities',{cache:'no-store'});
      const data=await response.json();
      if(!response.ok || !Array.isArray(data.traditions)) return;
      if(typeof data.sidereal_convention?.label==='string') siderealLabel=data.sidereal_convention.label;
      if(typeof data.date_bounds?.min==='string' && typeof data.date_bounds?.max==='string') dateBounds={min:data.date_bounds.min,max:data.date_bounds.max};
      for(const option of $('tradition').options) {
        const supported=data.traditions.includes(option.value);
        option.disabled=!supported; option.hidden=!supported;
      }
      if(!data.traditions.includes($('tradition').value)) $('tradition').value=data.traditions.includes('western') ? 'western' : '';
      setKind(kind);
    } catch(_) {}
  }
  function populateBirth(request,chart,localInputs) {
    place=localInputs?.place || chart.place || null; $('place-query').value=place?.name || ''; $('selected-place').hidden=!place;
    text('place-name',place?.label || ''); text('place-status',place ? 'City centre · '+place.timezone : '');
    $('birth-date').value=localInputs?.date || request.birthday || request.birth?.local_datetime.split('T')[0] || '';
    $('birth-time').value=localInputs?.time || request.birth?.local_datetime.split('T')[1] || '';
    const fold=localInputs?.fold ?? request.birth?.fold;
    if(fold!==undefined && fold!==null) { $('fold-field').hidden=false; $('birth-fold').value=String(fold); }
  }
  function showChart(show) {
    document.body.classList.toggle('chart-view',show);
    document.querySelector('.intro').hidden = show;
    $('observatory').hidden = !show;
    $('chart-content').hidden = !show || !record;
    $('return-chart').hidden = !record;
  }
  function stopReading() {
    revision++; controller?.abort(); controller = null; setBusy(false);
    text('reading-status',record ? 'Interpretation stopped. Your chart is still available.' : 'Calculation cancelled.');
    if (!record) text('phase','Calculation cancelled');
    $('retry').hidden = !record; if (record) record.complete = false;
  }
  $('edit-inputs').addEventListener('click',() => {
    if (controller) stopReading();
    if (record) {
      let request=record.request.chart_request, chart=record.metadata.chart;
      // Older saved transit readings can still return to their original birth inputs.
      if(request.chart_kind==='transit') { request=request.natal_request; chart=chart.natal_chart; }
      $('tradition').value=request.tradition || chart.tradition || 'western';
      setKind(request.chart_kind); populateBirth(request,chart,record.request.local_inputs);
      if(request.chart_kind==='horoscope') $('horoscope-sign').value=request.sun_sign || '';

    }
    showChart(false); $('generate').focus();
  });
  $('return-chart').addEventListener('click',() => { if(record) { showChart(true); $('chart-heading').focus(); } });
  $('close-selection').addEventListener('click',() => {
    const previous=selected; selectPlanet(null);
    if(previous) $('planet-nodes').querySelector('[data-planet="'+previous+'"]').focus();
  });
  $('selection').addEventListener('keydown',event => { if(event.key === 'Escape') $('close-selection').click(); });
  function resetFold() { $('fold-field').hidden = true; $('birth-fold').value = ''; }
  for (const name of entryKinds) $('kind-'+name).addEventListener('click',() => setKind(name));
  for (const id of ['birth-date','birth-time']) $(id).addEventListener('input',resetFold);
  function clearPlace() { place = null; $('selected-place').hidden = true; resetFold(); }
  function closePlaceResults() {
    clearTimeout(searchTimer); searchRevision++; searchController?.abort();
    $('place-results').replaceChildren(); text('place-status','');
  }
  $('place-clear').addEventListener('click',() => { clearPlace(); closePlaceResults(); $('place-query').value = ''; $('place-query').focus(); });
  $('place-query').addEventListener('input',event => {
    clearPlace(); closePlaceResults();
    if (!event.isComposing && $('place-query').value.trim().length >= 2) searchTimer = setTimeout(searchPlaces,300);
  });
  $('place-query').addEventListener('compositionend',() => {
    clearTimeout(searchTimer);
    if ($('place-query').value.trim().length >= 2) searchTimer = setTimeout(searchPlaces,300);
  });
  $('place-query').addEventListener('keydown',event => {
    if (event.isComposing) return;
    if (event.key === 'Enter') { event.preventDefault(); searchPlaces(); }
    if (event.key === 'ArrowDown' && $('place-results').firstElementChild) { event.preventDefault(); $('place-results').firstElementChild.focus(); }
    if (event.key === 'Escape') { event.preventDefault(); closePlaceResults(); }
  });
  $('place-results').addEventListener('keydown',event => {
    if (event.key === 'Escape') { event.preventDefault(); closePlaceResults(); $('place-query').focus(); }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const next = event.key === 'ArrowDown' ? event.target.nextElementSibling : event.target.previousElementSibling;
      (next || $('place-query')).focus();
    }
  });
  $('place-fields').addEventListener('focusout',event => {
    if (!$('place-fields').contains(event.relatedTarget)) closePlaceResults();
  });
  $('place-search').addEventListener('click',searchPlaces);
  async function searchPlaces() {
    clearTimeout(searchTimer);
    const query = $('place-query').value.trim();
    if (query.length < 2) { text('place-status','Enter at least two letters of a city name.'); return; }
    const version = ++searchRevision;
    searchController?.abort(); searchController = new AbortController();
    const signal = searchController.signal;
    $('place-results').replaceChildren(); text('place-status','Finding cities…');
    const timeout = setTimeout(() => searchController?.signal === signal && searchController.abort(),15000);
    try {
      const response = await fetch('/astrology/places',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query}),signal,cache:'no-store'});
      const data = await response.json();
      if (version !== searchRevision) return;
      if (!response.ok) throw new Error(data.message || 'City search is unavailable. Please try again.');
      for (const result of data.places) {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'place-result';
        button.append(document.createTextNode(result.label));
        const detail = document.createElement('small'); detail.textContent = result.timezone.replaceAll('_',' '); button.append(detail);
        button.addEventListener('click',() => {
          place = result; closePlaceResults(); $('selected-place').hidden = false;
          text('place-name',result.label); text('place-status','City centre · '+result.timezone.replaceAll('_',' '));
          $('place-query').value = result.name; resetFold(); message('form-error',''); $('place-query').focus();
        });
        $('place-results').append(button);
      }
      text('place-status',data.places.length ? `${data.places.length} matching ${data.places.length === 1 ? 'city' : 'cities'}. Choose your location.` : 'No matching city found. Try a nearby city or another spelling.');
    } catch (error) {
      if (version === searchRevision) text('place-status',error.name === 'AbortError' ? 'City search timed out. Try again.' : error.message);
    } finally { clearTimeout(timeout); }
  }
  function requestFromForm() {
    const chart_request = {chart_kind:kind,tradition:$('tradition').value};
    const date=$('birth-date').value, time=$('birth-time').value;
    if(!date) throw new Error('Enter your birth date.');
    const completeRequired=kind==='natal' || $('tradition').value==='vedic';
    if(completeRequired && !time) throw new Error('Enter your recorded local birth time.');
    if(completeRequired && !place) throw new Error('Find and select your birthplace first.');
    if(!['western','vedic'].includes($('tradition').value)) throw new Error('Choose Western or Vedic.');
    if($('place-query').value.trim() && !place) throw new Error('Choose a matching birthplace, or clear the optional city field.');
    let fold;
    if(time && place) {
      chart_request.place_id=place.id;
      chart_request.birth={local_datetime:`${date}T${time}`};
      if(!$('fold-field').hidden) {
        if(!$('birth-fold').value) throw new Error('Choose which occurrence of this repeated clock time applies.');
        fold=Number($('birth-fold').value); chart_request.birth.fold=fold;
      }
    }
    if(kind==='horoscope') {
      chart_request.birthday=date;
      if($('tradition').value==='western' && $('horoscope-sign').value) chart_request.sun_sign=$('horoscope-sign').value;
    }
    // Keep optional drafts for explicit browser saves; never send them to the reading endpoint.
    return {chart_request,question:'',local_inputs:{date,time,place:place ? clone(place) : null,fold}};
  }
  function setBusy(busy) {
    $('generate').disabled = busy; $('cancel').hidden = !busy; $('stop-reading').hidden = !busy || !record;
    $('retry').disabled = busy; $('save').disabled = busy;
    $('share-reading').disabled = busy || !record?.complete;
    for (const id of ['kind-natal','kind-horoscope','tradition','horoscope-sign','place-search','place-clear','place-query','birth-date','birth-time','birth-fold']) $(id).disabled = busy;
    $('birth-fields').disabled = busy;
    $('horoscope-fields').disabled=busy || kind!=='horoscope' || $('tradition').value==='vedic';
    $('chart-form').setAttribute('aria-busy',String(busy));
  }
  $('chart-form').addEventListener('submit',event => {
    event.preventDefault();
    try { runReading(requestFromForm()); } catch(error) { message('form-error',error.message); }
  });
  $('cancel').addEventListener('click',stopReading);
  $('stop-reading').addEventListener('click',stopReading);
  $('retry').addEventListener('click',() => { if (record) runReading(clone(record.request),true); });
  async function runReading(payload,retry = false) {
    const savedId = retry ? record?.id : undefined;
    searchRevision++; searchController?.abort(); $('place-results').replaceChildren();
    const version = ++revision; controller?.abort(); controller = new AbortController();
    const signal = controller.signal;
    let timedOut = false, terminal = false, metadataSeen = false;
    const timeout = setTimeout(() => { timedOut = true; if (!signal.aborted) controller?.signal === signal && controller.abort(); },120000);
    if (!retry) {
      showChart(false); record = null; selected = null; $('return-chart').hidden=true; $('chart-content').hidden = true; $('selection').hidden = true; $('replay').hidden = true;
      createField(); text('chart-time-label','CALCULATING'); text('chart-kind-label',kind === 'natal' ? 'BIRTH CHART' : 'SKY NOW');
    } else { record.text = ''; record.complete = false; renderProse(); }
    message('form-error',''); message('reading-error',''); text('save-status',''); $('retry').hidden = true; setBusy(true);
    text('reading-status','Calculating your chart…');
    let reader;
    try {
      const response = await fetch('/astrology/read/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chart_request:payload.chart_request,question:payload.question}),signal,cache:'no-store'});
      if (version !== revision) return;
      if (!response.ok) {
        const failure = await response.json();
        if (failure.code === 'ambiguous_birth_time') $('fold-field').hidden = false;
        throw new Error(failure.message || 'The chart could not be calculated. Check your inputs.');
      }
      if (!response.body) throw new Error('Streaming is unavailable in this browser.');
      const fixture = response.headers.get('X-Oracle-Test-Fixture') === '1';
      reader = response.body.getReader();
      const decoder = new TextDecoder(); let buffer = '', bytes = 0;
      function handleFrame(frame) {
        const lines = frame.split('\n');
        const event = lines.find(line => line.startsWith('event:'))?.slice(6).trim();
        const raw = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
        if (!raw) return;
        const data = JSON.parse(raw);
        if (event === 'metadata') {
          if (metadataSeen || !validChart(data.chart)) throw new Error('The chart response could not be read.');
          metadataSeen = true;
          const stableRequest = clone(payload);
          if (data.chart_kind !== 'natal') stableRequest.chart_request.instant_utc = data.chart.inputs.utc;
          record = {metadata:data,request:stableRequest,text:'',complete:false,fixture,id:savedId};
          renderChart(data.chart); $('stop-reading').hidden=false; text('reading-status',fixture ? 'Test interpretation (fixture)' : 'Your reading is unfolding…');
        } else if (event === 'token') {
          if (!metadataSeen || typeof data.token !== 'string') throw new Error('The reading arrived without chart details.');
          record.text += data.token; renderProse();
        } else if (event === 'error') {
          terminal = true;
          throw new Error(data.message || data.error || 'Interpretation is unavailable. Your chart is still ready.');
        } else if (event === 'done') {
          if (!metadataSeen) throw new Error('The server returned no chart.');
          if (!record.text.trim()) throw new Error('No interpretation was returned. Your chart is ready; try the interpretation again.');
          terminal = true; record.complete = true;
          text('reading-status',fixture ? 'Test interpretation (fixture) · complete' : 'Your reading is complete.');
          text('save','Save reading');
        }
      }
      while (!terminal) {
        const {done,value} = await reader.read();
        if (version !== revision) return;
        if (done) { buffer += decoder.decode(); break; }
        bytes += value.byteLength;
        if (bytes > 1500000) throw new Error('The reading exceeded its size limit. Your chart is still available.');
        buffer = (buffer + decoder.decode(value,{stream:true})).replace(/\r\n/g,'\n');
        let boundary;
        while ((boundary = buffer.indexOf('\n\n')) >= 0 && !terminal) {
          const frame = buffer.slice(0,boundary); buffer = buffer.slice(boundary+2); handleFrame(frame);
        }
      }
      if (!terminal && buffer.trim()) handleFrame(buffer);
      if (!terminal) throw new Error('The reading was interrupted. Retry interpretation to keep the same chart.');
    } catch(error) {
      if (version !== revision) return;
      const safe = timedOut ? 'Interpretation timed out. Your chart remains available; you can retry.' : error.name === 'AbortError' ? 'Reading cancelled.' : error.message;
      message(record ? 'reading-error' : 'form-error',safe);
      text('reading-status',record ? 'Chart ready · interpretation incomplete' : '');
      $('retry').hidden = !record;
      if (!record) { text('chart-time-label','A MOMENT AWAITS'); text('phase','Check the chart inputs'); }
    } finally {
      clearTimeout(timeout); if (reader) { try { await reader.cancel(); } catch(_) {} }
      if (version === revision) { controller = null; setBusy(false); }
    }
  }
  function validChart(chart) {
    return chart && chart.schema_version === 1 && Object.keys(kindNames).includes(chart.chart_kind) && typeof chart.inputs?.utc === 'string'
      && [undefined,'western','vedic'].includes(chart.tradition)
      && (isVedic(chart) ? vedicBodies : westernBodies).every(name => chart.planets?.[name] && Number.isFinite(chart.planets[name].longitude) && typeof chart.planets[name].sign === 'string')
      && Array.isArray(chart.major_aspects)
      && (chart.chart_kind!=='transit' || (chart.natal_chart?.chart_kind==='natal' && validChart(chart.natal_chart) && Array.isArray(chart.transit_aspects)))
      && (!isVedic(chart) || (chart.zodiac==='sidereal' && (chart.ayanamsa?.name==='Lahiri' || (chart.ayanamsa?.convention_id==='iae-2021' && chart.ayanamsa?.name==='Indian Astronomical Ephemeris (2021 convention)')) && Array.isArray(chart.vedic_aspects) && vedicBodies.every(name=>typeof chart.planets[name].nakshatra?.name==='string' && Number.isInteger(chart.planets[name].nakshatra.pada) && chart.planets[name].nakshatra.pada>=1 && chart.planets[name].nakshatra.pada<=4)))
      && (chart.chart_kind!=='horoscope' || (isVedic(chart) ? typeof chart.horoscope?.moon_sign==='string' && chart.horoscope.scope==='general_moon_sign' && typeof chart.horoscope.nakshatra?.name==='string' : typeof chart.horoscope?.sun_sign==='string' && chart.horoscope.scope==='general_sun_sign'));
  }
  function aspectLabel(a,vedic,kind) {
    return vedic ? `${a.body_1} → ${a.body_2} · ${ordinal(a.house_distance)}-sign glance` : `${kind==='transit' ? 'Today’s ' : ''}${a.body_1} ${a.aspect} ${a.body_2} · ${a.orb.toFixed(1)}° orb`;
  }
  function horoscopeSignSource(source) {
    return source==='natal_calculation' ? 'Sun sign calculated from your birth date, time and birthplace.' : source==='user_selected' ? 'You selected this sign.' : 'Sign estimated from birthday ranges; boundary dates can vary.';
  }
  function chartTitle(chart) { return chart.chart_kind==='horoscope' ? horoscopeSign(chart)+(isVedic(chart) ? ' Moon today' : ' today') : ({natal:isVedic(chart) ? 'Your Vedic birth chart' : 'Your birth chart',current:'The sky now',transit:'Your personal transits'}[chart.chart_kind]); }
  function chartAspects(chart) { return isVedic(chart) ? chart.vedic_aspects : chart.chart_kind==='transit' ? chart.transit_aspects.map(a=>({...a,body_1:a.transit_body,body_2:'Natal '+a.natal_body})) : chart.major_aspects; }
  function renderChart(chart) {
    showChart(true); $('replay').hidden = false; text('save','Save chart');
    text('chart-heading',chartTitle(chart));
    text('chart-guide',chart.chart_kind==='transit' ? 'Glowing symbols: today. Small outer markers: your birth chart.' : chart.chart_kind==='horoscope' ? 'A general '+horoscopeSign(chart)+(isVedic(chart) ? ' Moon-sign' : ' Sun-sign')+' reading. Symbols show today’s sky.' : 'Choose a symbol to explore its meaning.');
    text('reading-title',chart.chart_kind==='transit' ? 'Today, through your birth chart' : chart.chart_kind==='horoscope' ? horoscopeSign(chart)+(isVedic(chart) ? ' Moon today' : ' today') : 'What the sky suggests');
    text('edit-inputs',chart.chart_kind === 'natal' ? 'Edit birth details' : 'Edit details');
    $('chart-heading').focus({preventScroll:true}); window.scrollTo({top:0,behavior:'instant'});
    text('chart-kind-label',chart.chart_kind==='current' ? (chart.place ? 'LOCAL SKY NOW' : 'GLOBAL SKY NOW') : (isVedic(chart) ? 'VEDIC · ' : '')+kindNames[chart.chart_kind].toUpperCase());
    text('chart-time-label',chart.inputs.utc.replace('T',' · ').replace('Z',' UTC'));
    selected = null; createField(chart); field.reveal();
    $('planet-list').replaceChildren();
    for (const [name,p] of Object.entries(chart.planets)) {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'planet'; button.dataset.planet = name; button.setAttribute('aria-pressed','false');
      button.setAttribute('aria-label',`${name}, ${position(p)}${p.retrograde ? ', retrograde' : ''}${p.whole_sign_house ? ', house '+p.whole_sign_house : ''}`);
      for (const [className,value] of [['glyph',glyphs[name]],['name',name],['position',position(p)],['motion',[p.whole_sign_house ? 'HOUSE '+p.whole_sign_house : '', p.retrograde ? '℞' : ''].filter(Boolean).join(' · ')]]) {
        const span = document.createElement('span'); span.className = className; span.textContent = value;
        if (className === 'glyph') span.setAttribute('aria-hidden','true'); button.append(span);
      }
      button.addEventListener('click',() => selectPlanet(selected === name ? null : name)); $('planet-list').append(button);
    }
    selectPlanet(null);
    text('angles',chart.ascendant ? `Rising sign: ${position(chart.ascendant)} · Midheaven: ${position(chart.midheaven)} · Whole Sign houses` : 'Global sky · Houses and rising sign depend on a location and are omitted here.');
    if(chart.chart_kind==='transit') text('angles','Today’s planets compared with your natal placements · Houses refer to your birth chart.');
    if(isVedic(chart) && chart.chart_kind==='natal') text('angles',`Lagna: ${position(chart.ascendant)} · Moon sign: ${chart.planets.Moon.sign} · ${nakshatraLabel(chart.planets.Moon.nakshatra)}`);
    if(chart.chart_kind==='horoscope') text('angles',isVedic(chart) ? `${horoscopeSign(chart)} Moon · ${nakshatraLabel(chart.horoscope.nakshatra)} · Calculated from your birth details` : horoscopeSign(chart)+' · General Sun-sign horoscope · '+horoscopeSignSource(chart.horoscope.sign_source));
    renderDetails(chart); renderProse();
  }
  function selectPlanet(name) {
    selected = name; activeAspect = null; field.selectPlanet(name); field.selectAspect?.(null);
    $('selection').scrollTop=0;
    $('observatory').classList.toggle('inspecting',!!name);
    $('selection').hidden=!name;
    for (const button of $('planet-list').children) button.setAttribute('aria-pressed',String(button.dataset.planet === name));
    if (!record || !name) return;
    const chart = record.metadata.chart, p=chart.planets[name];
    const vedic=isVedic(chart), meanings=vedic ? VedicMeanings : AstrologyMeanings;
    text('selection-label',name.toUpperCase()+' · '+(p.retrograde ? 'RETROGRADE' : 'DIRECT'));
    text('selection-title',glyphs[name]+' '+name);
    text('selection-copy',position(p)+(p.whole_sign_house ? ' · House '+p.whole_sign_house : '')+' · '+meanings.planet(name));
    const root=$('placement-meaning'); root.replaceChildren();
    const sections=vedic ? meanings.placement(name,p,chart.chart_kind) : meanings.placement(name,p.sign,p.whole_sign_house,chart.chart_kind);
    if(vedic && chart.chart_kind==='horoscope' && p.moon_sign_house) sections.push({title:`House ${p.moon_sign_house} from your Moon sign`,text:`Today’s ${name} falls in the ${ordinal(p.moon_sign_house)} sign counted from your natal Moon sign, ${horoscopeSign(chart)}. This is a Moon-sign reference, separate from the houses of your birth chart.`});
    if(chart.chart_kind==='transit' && p.natal_house) sections.push({title:'In your natal house '+p.natal_house,text:'Today’s '+name+' falls in house '+p.natal_house+' of your birth chart. '+meanings.placement(name,p.sign,p.natal_house,'natal')[1].text.replace('With '+name+' here,','As this planet passes through,')});
    if(p.retrograde) sections.push({title:'Retrograde',text:meanings.retrograde(name,chart.chart_kind)});
    for(const section of sections) {
      const heading=document.createElement('h3'), paragraph=document.createElement('p');
      heading.textContent=section.title; paragraph.textContent=section.text; root.append(heading,paragraph);
    }
    const aspects=$('aspect-meanings'); aspects.replaceChildren();
    const heading=document.createElement('h3'); heading.textContent=vedic ? 'Planetary glances · Graha drishti' : chart.chart_kind==='transit' ? 'Connections to your birth chart' : chart.chart_kind==='natal' ? 'Connections in your birth chart' : 'Connections in today’s sky'; aspects.append(heading);
    const related=chartAspects(chart).filter(a=>a.body_1===name || a.body_2===name);
    if(!related.length) { const empty=document.createElement('p'); empty.textContent=vedic ? 'No full planetary glances connect this graha with another body under this chart’s rules.' : 'No major aspects within the chart’s configured orbs.'; aspects.append(empty); }
    for(const aspect of related) {
      const detail=document.createElement('details'), summary=document.createElement('summary'), paragraph=document.createElement('p');
      detail.className='aspect-card';
      summary.textContent=aspectLabel(aspect,vedic,chart.chart_kind);
      paragraph.textContent=vedic ? meanings.aspect(aspect.body_1,aspect.body_2,aspect.aspect,chart.chart_kind,aspect.house_distance) : chart.chart_kind==='transit' ? 'Today’s '+aspect.transit_body+' at '+position(chart.planets[aspect.transit_body])+' connects with your natal '+aspect.natal_body+' at '+position(chart.natal_chart.planets[aspect.natal_body])+'. '+meanings.aspect(aspect.transit_body,aspect.natal_body,aspect.aspect,'transit') : meanings.aspect(aspect.body_1,aspect.body_2,aspect.aspect,chart.chart_kind);
      detail.append(summary,paragraph); aspects.append(detail);
      detail.addEventListener('toggle',()=>{
        if(!aspects.contains(detail)) return;
        if(detail.open) {
          for(const other of aspects.querySelectorAll('details')) if(other!==detail) other.open=false;
          activeAspect=aspect; field.selectAspect?.(aspect);
        } else if(!aspects.querySelector('details[open]')) { activeAspect=null; field.selectAspect?.(null); }
      });
    }
  }
  function renderDetails(chart) {
    const root = $('chart-details'); root.replaceChildren();
    const paragraph = document.createElement('p');
    paragraph.textContent = `${chart.engine.library} ${chart.engine.library_version} · ${chart.engine.ephemeris_model}. ${isVedic(chart) ? 'Sidereal, '+ayanamsaLabel(chart)+' ayanamsa '+Number(chart.ayanamsa.degrees).toFixed(4)+'°, mean lunar nodes' : 'Tropical'}, apparent geocentric positions. ${chart.place ? 'City-centre coordinates from GeoNames; timezone '+chart.place.timezone+'. ' : ''}Star particles and radial distances are illustrative.`;
    root.append(paragraph);
    if (chart.chart_kind === 'natal') {
      const birth = document.createElement('p'); birth.textContent = `Recorded local time: ${record.request.chart_request.birth.local_datetime.replace('T',' ')} · Resolved UTC: ${chart.inputs.utc}`; root.append(birth);
    }
    const table = document.createElement('table');
    const caption = document.createElement('caption'); caption.textContent = isVedic(chart) ? 'Calculated planetary glances' : 'Calculated major aspects'; caption.className = 'sr-only'; table.append(caption);
    const head = document.createElement('thead'), tr = document.createElement('tr');
    for (const name of (isVedic(chart) ? ['From / To','Aspect','Sign distance'] : ['Bodies','Aspect','Orb'])) { const th = document.createElement('th'); th.scope='col'; th.textContent=name; tr.append(th); } head.append(tr); table.append(head);
    const body = document.createElement('tbody');
    for (const a of chartAspects(chart)) { const row = document.createElement('tr'); for (const value of [a.body_1+' / '+a.body_2,a.aspect,isVedic(chart) ? String(a.house_distance) : a.orb.toFixed(2)+'°']) { const cell=document.createElement('td'); cell.textContent=value; row.append(cell); } body.append(row); } table.append(body); root.append(table);
    if (chart.whole_sign_cusps) { const houses = document.createElement('p'); houses.textContent = chart.whole_sign_cusps.map(h => `House ${h.house}: ${h.sign}`).join(' · '); root.append(houses); }
    for (const warning of [...(chart.provenance.warnings || []),...(chart.provenance.limitations || [])]) { const p=document.createElement('p'); p.textContent=warning; root.append(p); }
  }
  function escapeHTML(value) { return String(value).replace(/[&<>"']/g,c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function inline(value) { return escapeHTML(value).replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/\*([^*]+)\*/g,'<em>$1</em>'); }
  function markdown(value) {
    return value.trim().split(/\n\s*\n/).filter(Boolean).map(block => {
      if (/^#{1,6}\s/.test(block)) return '<h3>'+inline(block.replace(/^#{1,6}\s+/,''))+'</h3>';
      if (block.split('\n').every(line => /^\s*[-*]\s+/.test(line))) return '<ul>'+block.split('\n').map(line => '<li>'+inline(line.replace(/^\s*[-*]\s+/,''))+'</li>').join('')+'</ul>';
      return '<p>'+inline(block).replace(/\n/g,'<br>')+'</p>';
    }).join('');
  }
  function renderProse() {
    $('share-reading').disabled = Boolean(controller) || !record?.complete;
    const layers = ReadingLayers.parse(record?.text || '');
    $('heart').hidden = !layers.heart; $('heart').innerHTML = markdown(layers.heart);
    $('depth').hidden = !layers.depth; $('depth-text').innerHTML = markdown(layers.depth);
  }
  $('pause').addEventListener('click',() => { paused=!paused; field.setPaused(paused); $('pause').setAttribute('aria-pressed',String(paused)); text('pause',paused ? 'Resume motion' : 'Pause motion'); });
  $('replay').addEventListener('click',() => { if(record) { createField(record.metadata.chart); field.selectPlanet(selected); field.selectAspect?.(activeAspect); field.reveal(); } });
  function savedRecords() {
    try { const entries=JSON.parse(localStorage.getItem(journalKey) || '[]'); return Array.isArray(entries) ? entries.filter(e => e && typeof e.id === 'string' && validChart(e.metadata?.chart) && typeof e.text === 'string' && e.request?.chart_request).slice(0,20) : []; }
    catch(_) { return []; }
  }
  $('save').addEventListener('click',() => {
    if (!record) return;
    try {
      const entries=savedRecords(), entry=clone(record);
      entry.id=entry.id || entry.metadata.canonical_reading_id; entry.saved_at=new Date().toISOString();
      localStorage.setItem(journalKey,JSON.stringify([entry,...entries.filter(e => e.id!==entry.id)].slice(0,20)));
      record.id=entry.id; text('save-status','Saved in this browser, including the chart inputs and reading.'); text('save','Saved');
    } catch(_) { text('save-status','This browser could not save the chart. You can still download it.'); }
  });
  function showSaved() {
    const entries=savedRecords(); $('saved-panel').hidden=false; $('saved-list').replaceChildren();
    if (!entries.length) { const p=document.createElement('p'); p.className='help'; p.textContent='No saved charts yet. Use Save chart or Save reading after a reveal.'; $('saved-list').append(p); }
    for (const entry of entries) {
      const row=document.createElement('div'); row.className='saved-entry'; const open=document.createElement('button'); open.type='button';
      open.textContent=(isVedic(entry.metadata.chart) ? 'Vedic · ' : 'Western · ')+kindNames[entry.metadata.chart_kind]+(entry.metadata.chart.horoscope ? ' · '+horoscopeSign(entry.metadata.chart) : entry.metadata.chart.place ? ' · '+entry.metadata.chart.place.name : entry.metadata.chart_kind==='current' ? ' · Global sky' : '');
      const detail=document.createElement('small'); detail.textContent=new Date(entry.saved_at).toLocaleString()+' · '+(entry.complete ? 'Reading' : 'Chart'); open.append(detail);
      open.addEventListener('click',() => {
        revision++; controller?.abort(); controller=null; setBusy(false); record=clone(entry); renderChart(record.metadata.chart);
        message('reading-error',''); message('form-error',''); text('reading-status',entry.fixture ? 'Saved test interpretation (fixture)' : entry.complete ? 'Saved reading · reopened without recalculation' : 'Saved chart · interpretation incomplete');
        $('retry').hidden=entry.complete; text('save','Saved'); text('save-status','Stored in this browser.'); $('saved-panel').hidden=true;
        $('chart-heading').focus();
      });
      const remove=document.createElement('button'); remove.type='button'; remove.className='quiet'; remove.textContent='Remove'; remove.setAttribute('aria-label','Remove saved '+kindNames[entry.metadata.chart_kind]);
      remove.addEventListener('click',() => {
        if (!confirm('Remove this saved chart and reading from this browser?')) return;
        try { localStorage.setItem(journalKey,JSON.stringify(savedRecords().filter(e => e.id!==entry.id))); showSaved(); }
        catch(_) { text('save-status','The saved chart could not be removed.'); }
      });
      row.append(open,remove); $('saved-list').append(row);
    }
    $('saved-title').focus();
  }
  $('saved-toggle').addEventListener('click',()=>showSaved()); $('saved-close').addEventListener('click',() => { $('saved-panel').hidden=true; $('saved-toggle').focus(); });
  function exportData() {
    const chart=record.metadata.chart, layers=ReadingLayers.parse(record.text);
    const placements=Object.entries(chart.planets).map(([name,p]) => `${name}: ${position(p)}${p.nakshatra ? ' · '+nakshatraLabel(p.nakshatra) : ''}${p.retrograde ? ' (retrograde)' : ''}${p.whole_sign_house ? ' · House '+p.whole_sign_house : p.natal_house ? ' · Natal house '+p.natal_house : ''}`).join('\n');
    const sections=[{title:'Planetary positions',text:placements}];
    if (chart.ascendant) sections.push({title:'Angles',text:`Ascendant: ${position(chart.ascendant)}\nMidheaven: ${position(chart.midheaven)}`});
    sections.push({title:isVedic(chart) ? 'Planetary glances' : 'Major aspects',text:chartAspects(chart).map(a => aspectLabel(a,isVedic(chart),chart.chart_kind)).join('\n') || 'No connections under the selected rules.'});
    const plain = value => value.replace(/^#{1,6}\s+/gm,'').replace(/\*\*([^*]+)\*\*/g,'$1').replace(/\*([^*]+)\*/g,'$1').replace(/`([^`]+)`/g,'$1').trim();
    if (layers.heart) sections.push({title:'Heart of the reading',text:plain(layers.heart)});
    if (layers.depth) sections.push({title:record.complete ? 'Full reading' : 'Partial interpretation',text:plain(layers.depth)});
    sections.push({title:'About this chart',text:`${chart.engine.library} ${chart.engine.library_version}, ${chart.engine.ephemeris_model}. ${isVedic(chart) ? 'Vedic sidereal ('+ayanamsaLabel(chart)+'), mean Rahu/Ketu' : 'Western tropical'} geocentric chart${chart.chart_kind==='transit' ? ', current planets mapped to natal Whole Sign houses' : chart.ascendant ? ', Whole Sign houses' : ', no local houses'}. Astrological interpretation is symbolic reflection. Decorative particles and radial distances are illustrative. Birth inputs and the question are omitted. ${record.fixture ? 'TEST INTERPRETATION: this prose is a development fixture.' : ''}`});
    if(chart.chart_kind==='horoscope') sections.unshift({title:isVedic(chart) ? 'General Moon-sign horoscope' : 'General Sun-sign horoscope',text:horoscopeSign(chart)+' · '+chart.horoscope.date_utc+' · '+(isVedic(chart) ? nakshatraLabel(chart.horoscope.nakshatra) : horoscopeSignSource(chart.horoscope.sign_source))});
    if(chart.chart_kind==='transit') sections.unshift({title:'Natal placements used for comparison',text:Object.entries(chart.natal_chart.planets).map(([name,p])=>name+': '+position(p)).join('\n')});
    return {title:chartTitle(chart),sections};
  }
  function download(blob,name) { const url=URL.createObjectURL(blob),a=document.createElement('a'); a.href=url; a.download=name; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url),30000); }
  function shareSnapshot() {
    // Render a separate chart: sharing never changes the live selection, animation or birth inputs.
    const source=document.createElement('canvas');
    source.style.cssText='position:fixed;left:-10000px;top:0;width:600px;height:600px;pointer-events:none';
    source.setAttribute('aria-hidden','true'); document.body.append(source);
    let exportField;
    try {
      exportField=new CelestialField(source,record.metadata.chart);
      exportField.setPaused(true); exportField.reveal();
      const canvas=document.createElement('canvas'); canvas.width=source.width; canvas.height=source.height;
      const ctx=canvas.getContext('2d'); ctx.fillStyle='#000'; ctx.fillRect(0,0,canvas.width,canvas.height); ctx.drawImage(source,0,0);
      return {canvas,content:{x:0,y:0,w:canvas.width,h:canvas.height}};
    } finally { exportField?.destroy(); source.remove(); }
  }
  $('share-reading').addEventListener('click',() => {
    if (!record?.complete || controller) return;
    try {
      AstrologyShare.open({title:(record.fixture ? 'TEST · ' : '')+(isVedic(record.metadata.chart) ? 'Vedic · ' : 'Western · ')+chartTitle(record.metadata.chart),layers:ReadingLayers.parse(record.text),snapshot:shareSnapshot(),reading:exportData()});
    } catch (_) { text('save-status','Sharing could not be opened. Please try again.'); }
  });
  $('export-text').addEventListener('click',() => { if(!record)return; const output=exportData(); download(new Blob([output.title+'\n\n'+output.sections.map(s=>s.title+'\n'+s.text).join('\n\n')],{type:'text/plain;charset=utf-8'}),'oracle-astrology.txt'); });
  function chartImage() {
    const canvas=document.createElement('canvas'); canvas.width=1200; canvas.height=1320;
    const ctx=canvas.getContext('2d'); ctx.fillStyle='#06090f'; ctx.fillRect(0,0,1200,1320);
    // Capture all placements, independent of the current selected-planet highlight.
    const wasPaused=paused; field.setPaused(true); field.reveal(); field.selectPlanet(null);
    const source=$('sky'), scale=Math.min(1120/source.width,1120/source.height);
    ctx.drawImage(source,(1200-source.width*scale)/2,80+(1120-source.height*scale)/2,source.width*scale,source.height*scale);
    field.selectPlanet(selected); field.selectAspect?.(activeAspect); field.setPaused(wasPaused);
    ctx.fillStyle='#e2eaf4'; ctx.textAlign='center'; ctx.font='36px Georgia'; ctx.fillText(chartTitle(record.metadata.chart),600,60);
    ctx.font='17px sans-serif'; ctx.fillStyle='#98abc1'; ctx.fillText(isVedic(record.metadata.chart) ? 'QUANTUM ORACLE · VEDIC · '+ayanamsaLabel(record.metadata.chart).toUpperCase()+' SIDEREAL' : 'QUANTUM ORACLE · TROPICAL ZODIAC',600,1220); ctx.fillText('Planetary positions · Expressive starlight',600,1255);
    return canvas.toDataURL('image/png');
  }
  $('export-image').addEventListener('click',() => { if(!record)return; const a=document.createElement('a'); a.href=chartImage(); a.download='oracle-chart.png'; a.click(); });
  $('export-pdf').addEventListener('click',() => {
    if(!record || pdfWorker)return;
    const button=$('export-pdf'); button.disabled=true; button.textContent='Preparing PDF…';
    let timeout;
    const finish=() => { clearTimeout(timeout); pdfWorker?.terminate(); pdfWorker=null; button.disabled=false; button.textContent='Download PDF'; };
    try {
      pdfWorker=new Worker('/static/reading-pdf-worker.js');
      timeout=setTimeout(() => { finish(); text('save-status','PDF export timed out. Try text or image export.'); },45000);
      pdfWorker.onmessage=event => { if(event.data.error) text('save-status','PDF export failed. Try again or download text.'); else download(event.data.blob,'oracle-astrology.pdf'); finish(); };
      pdfWorker.onerror=() => { finish(); text('save-status','PDF export is unavailable. Text and image export still work.'); };
      pdfWorker.postMessage({reading:exportData(),spreadImage:chartImage()});
    } catch(_) { finish(); text('save-status','PDF export is unavailable in this browser.'); }
  });
  function applyTheme(theme) { document.documentElement.dataset.theme=theme; text('theme-toggle',theme === 'light' ? 'Dark' : 'Light'); $('theme-toggle').setAttribute('aria-label',theme==='light' ? 'Switch to dark theme' : 'Switch to light theme'); }
  let theme='dark'; try { theme=localStorage.getItem('theme') === 'light' ? 'light' : 'dark'; } catch(_) {} applyTheme(theme);
  $('theme-toggle').addEventListener('click',() => { theme=theme==='dark'?'light':'dark'; applyTheme(theme); try { localStorage.setItem('theme',theme); } catch(_) {} });
  window.addEventListener('pagehide',() => { controller?.abort(); searchController?.abort(); field?.destroy(); pdfWorker?.terminate(); },{once:true});
  setKind('natal'); createField(); applyCapabilities();
})();
