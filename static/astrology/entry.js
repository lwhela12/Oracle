/* Astrology is discoverable only when the server enables it. */
(async () => {
  try {
    const response = await fetch('/astrology/capabilities', {cache:'no-store'});
    if (!response.ok || !(await response.json()).enabled) return;
    const choices = document.querySelector('.tradition-choices');
    if (!choices) return;
    const link = document.createElement('a');
    link.className = 'tradition-choice'; link.href = '/astrology/';
    link.innerHTML = '<span class="choice-emblem" data-emblem="astrology" aria-hidden="true">'+getTraditionEmblemSvg('astrology')+'</span><span class="choice-copy"><strong>Astrology</strong><span>Explore your birth chart or the sky now</span></span>';
    choices.append(link);
  } catch (_) { /* Existing readings do not depend on this optional feature. */ }
})();
