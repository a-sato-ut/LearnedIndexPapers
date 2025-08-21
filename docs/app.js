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
    el('div',{class:'citation-count'}, `被引用数: ${w.cited_by_count || 0}`),
    el('div',{class:'tags'}, ...tags),
    url ? el('a',{class:'btn', href:url, target:'_blank', rel:'noopener'}, 'Open') : null
  );
}

function filterPapers(papers, selectedTags, sortBy = 'citations'){
  const filtered = papers.filter(w=>{
    // AND検索: 選択された全てのタグが含まれている必要がある
    const okTag = !selectedTags.size || selectedTags.size === 0 || 
                  Array.from(selectedTags).every(tag => (w.tags||[]).includes(tag));
    return okTag;
  });
  
  // ソート順を適用
  if (sortBy === 'year') {
    // 出版年で降順ソート（新しい順）
    return filtered.sort((a, b) => (b.publication_year || 0) - (a.publication_year || 0));
  } else {
    // 被引用数で降順ソート（デフォルト）
    return filtered.sort((a, b) => (b.cited_by_count || 0) - (a.cited_by_count || 0));
  }
}

function mountTagFilter(allTags, stats){
  const container = document.getElementById('tag-checkboxes');
  container.innerHTML = '';
  
  // カテゴリごとにタグをグループ化
  const tagCategories = stats.tag_categories || {};
  const categoryGroups = {};
  
  // 各タグをカテゴリに分類
  [...allTags].forEach(tag => {
    const category = tagCategories[tag] || 'Other';
    if (!categoryGroups[category]) {
      categoryGroups[category] = [];
    }
    categoryGroups[category].push(tag);
  });
  
  // カテゴリごとにタグを表示
  Object.keys(categoryGroups).sort().forEach(category => {
    const tags = categoryGroups[category];
    
    // カテゴリヘッダー
    const categoryHeader = el('div', {class: 'category-header'}, category);
    container.appendChild(categoryHeader);
    
    // タグの使用頻度でソート
    const sortedTags = tags.sort((a, b) => {
      const countA = stats.by_tag[a] || 0;
      const countB = stats.by_tag[b] || 0;
      return countB - countA; // 使用頻度の高い順
    });
    
    // カテゴリ内のタグ
    const categoryContainer = el('div', {class: 'category-tags'});
    sortedTags.forEach(tag => {
      const count = stats.by_tag[tag] || 0;
      const label = el('label', {class: 'tag-checkbox'}, 
        el('input', {type: 'checkbox', value: tag}),
        el('span', {class: 'tag-text'}, `${tag} (${count})`)
      );
      categoryContainer.appendChild(label);
    });
    container.appendChild(categoryContainer);
  });
  
  return container;
}

function renderTopAuthors(stats){
  const ol = document.getElementById('top-authors');
  ol.innerHTML = '';
  for(const a of stats.top_authors||[]){
    const name = a.name;
    const papers = a.papers;
    const avgCitations = a.avg_citations.toFixed(1);
    const totalCitations = Math.round(papers * avgCitations);
    
    // 著者のイニシャルを取得（アバター用）
    const initials = name.split(' ').map(n => n.charAt(0)).join('').toUpperCase();
    
    const li = el('li', {},
      el('div', {class: 'author-rank'}, (stats.top_authors.indexOf(a) + 1).toString()),
      el('div', {class: 'author-avatar'}, initials),
      el('div', {class: 'author-info'},
        el('div', {class: 'author-name'}, name),
        el('div', {class: 'author-stats'},
          el('div', {class: 'paper-count'}, 
            el('span', {}, '📄'),
            `${papers} papers`
          ),
          el('div', {class: 'citation-count'}, 
            el('span', {}, '📊'),
            `avg ${avgCitations} citations`
          )
        )
      )
    );
    ol.appendChild(li);
  }
}

function renderCounters(stats){
  document.getElementById('total_works').textContent = stats.total_works;
  document.getElementById('citations_sum').textContent = stats.citations_sum;
  
  // UTCを日本時間に変換
  const utcDate = new Date(stats.last_updated);
  const jstString = utcDate.toLocaleString('ja-JP', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
  document.getElementById('last_updated').textContent = jstString;
  
  // 実行時間を表示
  const executionTime = stats.execution_time_seconds || 0;
  document.getElementById('execution_time').textContent = executionTime;
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



  const papers = citations.results||[];
  const allTags = new Set(papers.flatMap(p=>p.tags||[]));
  renderCounters(stats);
  renderCharts(stats);
  renderTopAuthors(stats);

  const tagContainer = mountTagFilter(allTags, stats);
  const list = document.getElementById('list');
  const clear = document.getElementById('clear');
  let currentSort = 'citations'; // デフォルトは被引用数順

  function refresh(){
    const selected = new Set();
    tagContainer.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
      selected.add(cb.value);
    });
    const view = filterPapers(papers, selected, currentSort);
    list.innerHTML = '';
    for(const w of view){ list.appendChild(renderCard(w)); }
  }

  tagContainer.addEventListener('change', refresh);
  clear.addEventListener('click', ()=>{ 
    tagContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false); 
    refresh(); 
  });

  // ソート機能
  const sortCitationsBtn = document.getElementById('sort-citations');
  const sortYearBtn = document.getElementById('sort-year');
  const sortBtns = [sortCitationsBtn, sortYearBtn];

  sortBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      // アクティブボタンを切り替え
      sortBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      // ソート順を更新
      if (btn === sortCitationsBtn) {
        currentSort = 'citations';
      } else {
        currentSort = 'year';
      }
      
      refresh();
    });
  });

  // フィルター開閉機能
  const filterToggle = document.getElementById('filter-toggle');
  const filterContent = document.getElementById('filter-content');
  const toggleIcon = filterToggle.querySelector('.toggle-icon');

  filterToggle.addEventListener('click', () => {
    const isCollapsed = filterContent.classList.contains('collapsed');
    if (isCollapsed) {
      filterContent.classList.remove('collapsed');
      filterContent.classList.add('expanded');
      toggleIcon.style.transform = 'rotate(180deg)';
    } else {
      filterContent.classList.remove('expanded');
      filterContent.classList.add('collapsed');
      toggleIcon.style.transform = 'rotate(0deg)';
    }
  });

  // タブ機能
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      
      // アクティブタブを切り替え
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      
      btn.classList.add('active');
      document.getElementById(`tab-${targetTab}`).classList.add('active');
    });
  });

  refresh();
})(); 