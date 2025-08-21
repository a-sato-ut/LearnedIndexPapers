async function loadJSON(path){
  const r = await fetch(path);
  if(!r.ok) throw new Error("Failed: "+path);
  return await r.json();
}

function el(tag, attrs={}, ...children){
  const e = document.createElement(tag);
  Object.entries(attrs).forEach(([k,v])=>{
    if(k === 'class') e.className = v; else if(k === 'html') e.innerHTML = v; else e.setAttribute(k, v);
  });
  for(const c of children){ if(typeof c === 'string') e.appendChild(document.createTextNode(c)); else if(c) e.appendChild(c); }
  return e;
}

function renderCard(w){
  const authors = (w.authorships||[]).map(a=>a.name).filter(Boolean).join(', ');
  const url = w.landing_page_url || (w.doi ? `https://doi.org/${w.doi.replace('https://doi.org/','')}` : null);
  const tags = (w.tags||[]).map(t=>el('span',{class:'tag'}, t));
  return el('article', {class:'card'},
    el('h3',{}, w.title||'(no title)'),
    el('div',{class:'meta'}, [authors || '(authors unknown)',' • ', w.host_venue||'(venue unknown)',' • ', w.publication_year||'–'].filter(Boolean).join(' ')),
    el('div',{class:'tags'}, ...tags),
    url ? el('a',{class:'btn', href:url, target:'_blank', rel:'noopener'}, 'Open') : null
  );
}

function filterPapers(papers, q, selectedTags){
  const k = (q||'').toLowerCase();
  return papers.filter(w=>{
    const hay = [w.title||'', w.host_venue||'', ...(w.authorships||[]).map(a=>a.name||'')].join('\n').toLowerCase();
    const okQ = !k || hay.includes(k);
    const okTag = !selectedTags.size || (w.tags||[]).some(t=>selectedTags.has(t));
    return okQ && okTag;
  });
}

function mountTagFilter(allTags){
  const sel = document.getElementById('tag-filter');
  sel.innerHTML = '';
  [...allTags].sort().forEach(t=>{
    sel.appendChild(el('option', {value:t}, t));
  });
  return sel;
}

function renderTopAuthors(stats){
  const ol = document.getElementById('top-authors');
  ol.innerHTML = '';
  for(const a of stats.top_authors||[]){
    const name = a.name;
    const li = el('li',{}, `${name}: ${a.papers} papers (avg cited_by ${a.avg_citations.toFixed(1)})`);
    ol.appendChild(li);
  }
}

function renderCounters(stats){
  document.getElementById('total_works').textContent = stats.total_works;
  document.getElementById('citations_sum').textContent = stats.citations_sum;
  document.getElementById('last_updated').textContent = stats.last_updated;
}

function renderCharts(stats){
  // Year chart
  const yc = document.getElementById('byYear').getContext('2d');
  const years = Object.keys(stats.by_year||{});
  const counts = Object.values(stats.by_year||{});
  new Chart(yc, {type:'bar', data:{labels:years, datasets:[{label:'papers / year', data:counts}]}});

  // Tag chart
  const tc = document.getElementById('byTag').getContext('2d');
  const tags = Object.keys(stats.by_tag||{}).slice(0,20);
  const vals = Object.values(stats.by_tag||{}).slice(0,20);
  new Chart(tc, {type:'bar', data:{labels:tags, datasets:[{label:'papers / tag (top20)', data:vals}]}});
}

(async function(){
  const citations = await loadJSON('data/citations.json');
  const stats = await loadJSON('data/stats.json');

  // Header meta
  const w = citations.work||{};
  const meta = document.getElementById('work-meta');
  meta.textContent = `${w.display_name||'Target work'} | OpenAlex: ${w.openalex_id||'N/A'} | cited_by_count: ${w.cited_by_count ?? 'N/A'}`;

  const papers = citations.results||[];
  const allTags = new Set(papers.flatMap(p=>p.tags||[]));
  renderCounters(stats);
  renderCharts(stats);
  renderTopAuthors(stats);

  const tagSel = mountTagFilter(allTags);
  const list = document.getElementById('list');
  const q = document.getElementById('q');
  const clear = document.getElementById('clear');

  function refresh(){
    const selected = new Set([...tagSel.selectedOptions].map(o=>o.value));
    const view = filterPapers(papers, q.value, selected);
    list.innerHTML = '';
    for(const w of view){ list.appendChild(renderCard(w)); }
  }

  q.addEventListener('input', refresh);
  tagSel.addEventListener('change', refresh);
  clear.addEventListener('click', ()=>{ q.value=''; [...tagSel.options].forEach(o=>o.selected=false); refresh(); });

  refresh();
})(); 