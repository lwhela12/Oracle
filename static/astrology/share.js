/* Local composition only. Native sharing starts only from the user's Share image click. */
(() => {
  'use strict';
  const dialog = document.createElement('dialog');
  dialog.className = 'astrology-share';
  dialog.setAttribute('aria-labelledby','astrology-share-title');
  dialog.innerHTML = `
    <div class="share-header"><div><p>A little wisdom to carry with you</p><h2 id="astrology-share-title">Share your reading</h2></div><button type="button" data-action="close" aria-label="Close share dialog">×</button></div>
    <div class="share-body"><div class="share-options">
      <p class="share-label">Format</p><div class="share-formats" role="group" aria-label="Card format"><button type="button" data-format="story" aria-pressed="true">Story<small>9:16 · Reels</small></button><button type="button" data-format="post" aria-pressed="false">Post<small>1:1 · Feed</small></button></div>
      <p class="share-label">Choose a quote</p><p class="share-hint">Choose a line from your reading for the image.</p><div class="share-quotes" role="group" aria-label="Quote choices"></div>
    </div><div class="share-preview"><button type="button" data-action="enlarge" aria-label="Enlarge reading image" disabled><img alt="Preview of your shareable astrology reading card"></button><p class="share-dimensions"></p><button type="button" class="share-enlarge" data-action="enlarge" disabled>Enlarge preview</button></div></div>
    <div class="share-actions"><button type="button" data-action="share" class="share-primary" disabled>Share image ↗</button><button type="button" data-action="download" disabled>Download image</button><p class="share-label">Full reading</p><button type="button" data-action="copy">Copy reading</button><button type="button" data-action="pdf">Download PDF</button><p class="share-feedback" role="status" aria-live="polite"></p></div>`;
  const enlarged = document.createElement('dialog');
  enlarged.className = 'astrology-share-enlarged';
  enlarged.setAttribute('aria-label','Reading image preview');
  enlarged.innerHTML = '<button type="button" aria-label="Close image preview">Close preview ×</button><img alt="Full-size shareable astrology reading card">';
  document.body.append(dialog,enlarged);
  const $ = selector => dialog.querySelector(selector);
  const button = action => $(`[data-action="${action}"]`);
  let session = 0, renderVersion = 0, current = null, quotes = [], activeQuote = 0, format = 'story';
  let imageFile = null, previewUrl = null, pdfWorker = null, pdfTimeout = null;
  const say = text => { $('.share-feedback').textContent = text; };
  function imageReady(ready) {
    for (const action of ['share','download']) button(action).disabled = !ready;
    dialog.querySelectorAll('[data-action="enlarge"]').forEach(node => { node.disabled = !ready; });
  }
  function download(blob,name) {
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = name; link.click();
    setTimeout(() => URL.revokeObjectURL(url),30000);
  }
  function stopPdf() {
    clearTimeout(pdfTimeout); pdfWorker?.terminate(); pdfWorker = null;
    button('pdf').disabled = false; button('pdf').textContent = 'Download PDF';
  }
  function cleanup() {
    session++; renderVersion++; imageFile = null; current = null; imageReady(false); stopPdf();
    if (enlarged.open) enlarged.close();
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null; $('.share-preview img').removeAttribute('src');
    enlarged.querySelector('img').removeAttribute('src');
  }
  dialog.addEventListener('close',cleanup);
  button('close').addEventListener('click',() => dialog.close());
  enlarged.querySelector('button').addEventListener('click',() => enlarged.close());
  dialog.querySelectorAll('[data-action="enlarge"]').forEach(node => node.addEventListener('click',() => {
    if (!previewUrl) return;
    enlarged.querySelector('img').src = previewUrl; enlarged.showModal();
  }));
  async function render() {
    const version = ++renderVersion, data = current, chosenFormat = format, quote = quotes[activeQuote] || '';
    imageFile = null; imageReady(false); say('Preparing image…');
    $('.share-preview').setAttribute('aria-busy','true');
    try {
      await OracleShareCard.ensureFonts();
      if (version !== renderVersion || !dialog.open) return;
      const canvas = OracleShareCard.compose({format:chosenFormat,title:data.title,quote,snapshot:data.snapshot});
      const blob = await new Promise((resolve,reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('Image unavailable')),'image/png'));
      if (version !== renderVersion || !dialog.open) return;
      const filename = `qoracle-astrology-${chosenFormat}.png`;
      imageFile = new File([blob],filename,{type:'image/png'});
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = URL.createObjectURL(blob); $('.share-preview img').src = previewUrl;
      $('.share-preview').dataset.format = chosenFormat;
      $('.share-dimensions').textContent = OracleShareCard.formats[chosenFormat].label;
      imageReady(true); say('');
    } catch (_) {
      if (version === renderVersion) say('The image could not be prepared. Choose a format to retry.');
    } finally {
      if (version === renderVersion) $('.share-preview').setAttribute('aria-busy','false');
    }
  }
  dialog.querySelectorAll('[data-format]').forEach(node => node.addEventListener('click',() => {
    format = node.dataset.format;
    dialog.querySelectorAll('[data-format]').forEach(item => item.setAttribute('aria-pressed',String(item === node)));
    render();
  }));
  button('download').addEventListener('click',() => { if (imageFile) { download(imageFile,imageFile.name); say('Image downloaded.'); } });
  button('share').addEventListener('click',async () => {
    if (!imageFile) return;
    const file = imageFile, version = session;
    // The PNG is already prepared, preserving the click's native share activation.
    if (!navigator.share || !navigator.canShare?.({files:[file]})) {
      download(file,file.name); say('Image downloaded. Upload it to your preferred social app.'); return;
    }
    button('share').disabled = true;
    try {
      await navigator.share({title:'Quantum Oracle · '+current.title,text:`${quotes[activeQuote] || current.title} — qoracle.app`,files:[file]});
      if (version === session) say('Image shared.');
    } catch (error) {
      if (version === session) say(error.name === 'AbortError' ? '' : 'Sharing is unavailable. Use Download image instead.');
    } finally { if (version === session && imageFile === file) button('share').disabled = false; }
  });
  button('copy').addEventListener('click',async () => {
    if (!current) return;
    const version = session;
    const text = ['Quantum Oracle',current.reading.title,...current.reading.sections.map(section => section.title+'\n'+section.text),'qoracle.app'].join('\n\n');
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
      else {
        const field = document.createElement('textarea'); field.value = text;
        field.style.cssText = 'position:fixed;opacity:0'; dialog.append(field); field.select();
        let copied; try { copied = document.execCommand('copy'); } finally { field.remove(); button('copy').focus(); }
        if (!copied) throw new Error('Clipboard unavailable');
      }
      if (version === session) say('Full reading copied.');
    } catch (_) { if (version === session) say('Copy was blocked. You can download the PDF instead.'); }
  });
  button('pdf').addEventListener('click',() => {
    if (!current || pdfWorker) return;
    button('pdf').disabled = true; button('pdf').textContent = 'Preparing…'; say('Preparing your PDF…');
    try {
      pdfWorker = new Worker('/static/reading-pdf-worker.js');
      pdfTimeout = setTimeout(() => { stopPdf(); say('PDF preparation timed out. Please try again.'); },45000);
      pdfWorker.onmessage = event => {
        if (event.data.blob instanceof Blob && !event.data.error) { download(event.data.blob,'qoracle-astrology.pdf'); say('PDF downloaded.'); }
        else say('PDF export failed. Please try again.');
        stopPdf();
      };
      pdfWorker.onerror = () => { stopPdf(); say('PDF export failed. Please try again.'); };
      pdfWorker.postMessage({reading:current.reading,spreadImage:current.snapshot.canvas.toDataURL('image/png')});
    } catch (_) { stopPdf(); say('PDF export is unavailable in this browser.'); }
  });
  window.AstrologyShare = {
    open(data) {
      if (dialog.open) return;
      current = data; session++; format = 'story'; activeQuote = 0;
      quotes = ReadingLayers.quotes(data.layers);
      const list = $('.share-quotes'); list.replaceChildren();
      if (!quotes.length) {
        const note = document.createElement('p'); note.className = 'share-hint'; note.textContent = 'No short quote is available. Your card will feature the chart.'; list.append(note);
      }
      quotes.forEach((quote,index) => {
        const option = document.createElement('button'); option.type = 'button'; option.textContent = quote; option.setAttribute('aria-pressed',String(index === 0));
        option.addEventListener('click',() => {
          activeQuote = index; list.querySelectorAll('button').forEach((item,i) => item.setAttribute('aria-pressed',String(i === index))); render();
        }); list.append(option);
      });
      dialog.querySelectorAll('[data-format]').forEach(item => item.setAttribute('aria-pressed',String(item.dataset.format === format)));
      dialog.showModal(); $('.share-body').scrollTop = 0; render();
    }
  };
})();
