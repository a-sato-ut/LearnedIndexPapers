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

function filterPapers(papers, selectedTags, selectedAuthors, sortBy = 'citations'){
  const filtered = papers.filter(w=>{
    // AND検索: 選択された全てのタグが含まれている必要がある
    const okTag = !selectedTags.size || selectedTags.size === 0 || 
                  Array.from(selectedTags).every(tag => (w.tags||[]).includes(tag));
    
    // AND検索: 選択された全ての著者が含まれている必要がある
    const paperAuthors = (w.authorships||[]).map(a=>a.name).filter(Boolean);
    const okAuthor = !selectedAuthors.size || selectedAuthors.size === 0 || 
                     Array.from(selectedAuthors).every(author => paperAuthors.includes(author));
    
    return okTag && okAuthor;
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

function mountAuthorFilter(allAuthors, stats){
  const container = document.getElementById('author-checkboxes');
  container.innerHTML = '';
  
  // 著者名でソート
  const sortedAuthors = [...allAuthors].sort((a, b) => a.localeCompare(b));
  
  // 著者の論文数を取得する関数
  const getAuthorPaperCount = (authorName) => {
    return stats.by_author ? stats.by_author[authorName] || 0 : 0;
  };
  
  sortedAuthors.forEach(author => {
    const count = getAuthorPaperCount(author);
    const label = el('label', {class: 'author-checkbox'}, 
      el('input', {type: 'checkbox', value: author}),
      el('span', {class: 'author-text'}, `${author} (${count} papers)`)
    );
    container.appendChild(label);
  });
  
  return container;
}

// 著者の主要タグを計算する関数
function getAuthorTopTags(authorName, papers) {
  // 著者の論文を取得
  const authorPapers = papers.filter(p => 
    (p.authorships || []).some(a => a.name === authorName)
  );
  
  // 著者の論文のタグを集計
  const tagCounts = {};
  authorPapers.forEach(paper => {
    (paper.tags || []).forEach(tag => {
      tagCounts[tag] = (tagCounts[tag] || 0) + 1;
    });
  });
  
  // 上位5つのタグを取得
  const topTags = Object.entries(tagCounts)
    .sort(([,a], [,b]) => b - a)
    .slice(0, 5)
    .map(([tag, count]) => ({ tag, count }));
  
  return topTags;
}

// フィルターを閉じる関数
function closeAllFilters() {
  // タグフィルターを閉じる
  const filterContent = document.getElementById('filter-content');
  const toggleIcon = document.querySelector('#filter-toggle .toggle-icon');
  filterContent.classList.remove('expanded');
  filterContent.classList.add('collapsed');
  toggleIcon.style.transform = 'rotate(0deg)';
  
  // 著者フィルターを閉じる
  const authorFilterContent = document.getElementById('author-filter-content');
  const authorToggleIcon = document.querySelector('#author-filter-toggle .toggle-icon');
  authorFilterContent.classList.remove('expanded');
  authorFilterContent.classList.add('collapsed');
  authorToggleIcon.style.transform = 'rotate(0deg)';
}

// グローバル変数として著者フィルター関数を定義
window.filterByAuthor = function(authorName) {
  // 論文一覧タブに切り替え
  const papersTab = document.querySelector('.tab-btn[data-tab="papers"]');
  const tabContents = document.querySelectorAll('.tab-content');
  const tabBtns = document.querySelectorAll('.tab-btn');
  
  // タブを切り替え
  tabBtns.forEach(b => b.classList.remove('active'));
  tabContents.forEach(c => c.classList.remove('active'));
  
  papersTab.classList.add('active');
  document.getElementById('tab-papers').classList.add('active');
  
  // 全てのフィルターを閉じる
  closeAllFilters();
  
  // 他の著者の選択をクリア
  const authorCheckboxes = document.querySelectorAll('#author-checkboxes input[type="checkbox"]');
  authorCheckboxes.forEach(cb => cb.checked = false);
  
  // 指定された著者を選択
  const targetCheckbox = document.querySelector(`#author-checkboxes input[value="${authorName}"]`);
  if (targetCheckbox) {
    targetCheckbox.checked = true;
    // フィルタリングを実行
    if (window.refreshPapers) {
      window.refreshPapers();
    }
  }
};

// 著者とタグの両方でフィルタリングする関数
window.filterByAuthorAndTag = function(authorName, tagName) {
  // 論文一覧タブに切り替え
  const papersTab = document.querySelector('.tab-btn[data-tab="papers"]');
  const tabContents = document.querySelectorAll('.tab-content');
  const tabBtns = document.querySelectorAll('.tab-btn');
  
  // タブを切り替え
  tabBtns.forEach(b => b.classList.remove('active'));
  tabContents.forEach(c => c.classList.remove('active'));
  
  papersTab.classList.add('active');
  document.getElementById('tab-papers').classList.add('active');
  
  // 全てのフィルターを閉じる
  closeAllFilters();
  
  // 他の選択をクリア
  const authorCheckboxes = document.querySelectorAll('#author-checkboxes input[type="checkbox"]');
  const tagCheckboxes = document.querySelectorAll('#tag-checkboxes input[type="checkbox"]');
  authorCheckboxes.forEach(cb => cb.checked = false);
  tagCheckboxes.forEach(cb => cb.checked = false);
  
  // 指定された著者を選択
  const targetAuthorCheckbox = document.querySelector(`#author-checkboxes input[value="${authorName}"]`);
  if (targetAuthorCheckbox) {
    targetAuthorCheckbox.checked = true;
  }
  
  // 指定されたタグを選択
  const targetTagCheckbox = document.querySelector(`#tag-checkboxes input[value="${tagName}"]`);
  if (targetTagCheckbox) {
    targetTagCheckbox.checked = true;
  }
  
  // フィルタリングを実行
  if (window.refreshPapers) {
    window.refreshPapers();
  }
};

// ページネーション用のグローバル変数
let currentPage = 1;
let authorsPerPage = 50;
let allAuthors = [];

function renderTopAuthors(stats, papers){
  allAuthors = stats.top_authors || [];
  currentPage = 1;
  
  // 著者数を表示
  document.getElementById('authors-count').textContent = allAuthors.length;
  
  renderAuthorsPage();
}

function renderAuthorsPage() {
  const tbody = document.getElementById('top-authors-tbody');
  tbody.innerHTML = '';
  
  const startIndex = (currentPage - 1) * authorsPerPage;
  const endIndex = startIndex + authorsPerPage;
  const pageAuthors = allAuthors.slice(startIndex, endIndex);
  
  for(let i = 0; i < pageAuthors.length; i++){
    const a = pageAuthors[i];
    const name = a.name;
    const papers = a.papers;
    const avgCitations = a.avg_citations.toFixed(1);
    const totalCitations = Math.round(papers * avgCitations);
    const rank = startIndex + i + 1;
    
    // 著者の主要タグを取得
    const topTags = getAuthorTopTags(name, window.allPapers || []);
    const tagsHtml = topTags.map(tag => 
      `<span class="tag-badge" onclick="filterByAuthorAndTag('${name}', '${tag.tag}')">${tag.tag} (${tag.count})</span>`
    ).join('');
    
    const tr = el('tr', {class: 'author-row'},
      el('td', {class: 'rank-cell'}, 
        el('div', {class: 'author-rank'}, rank.toString())
      ),
      el('td', {class: 'name-cell'}, 
        el('div', {class: 'author-name', onclick: `filterByAuthor('${name}')`}, name)
      ),
      el('td', {class: 'papers-cell'}, 
        el('div', {class: 'paper-count'}, 
          el('span', {}, '📄'),
          papers.toString()
        )
      ),
      el('td', {class: 'avg-citations-cell'}, 
        el('div', {class: 'avg-citations'}, avgCitations)
      ),
      el('td', {class: 'total-citations-cell'}, 
        el('div', {class: 'total-citations'}, totalCitations.toString())
      ),
      el('td', {class: 'tags-cell'}, 
        el('div', {class: 'tags-container', html: tagsHtml})
      )
    );
    tbody.appendChild(tr);
  }
  
  // ページネーション情報を更新
  updatePagination();
}

function updatePagination() {
  const totalPages = Math.ceil(allAuthors.length / authorsPerPage);
  const pageInfo = document.getElementById('page-info');
  const prevBtn = document.getElementById('prev-page');
  const nextBtn = document.getElementById('next-page');
  
  pageInfo.textContent = `${currentPage} / ${totalPages}`;
  prevBtn.disabled = currentPage === 1;
  nextBtn.disabled = currentPage === totalPages;
}

// ページネーションイベントリスナー
function setupPagination() {
  document.getElementById('prev-page').addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      renderAuthorsPage();
    }
  });
  
  document.getElementById('next-page').addEventListener('click', () => {
    const totalPages = Math.ceil(allAuthors.length / authorsPerPage);
    if (currentPage < totalPages) {
      currentPage++;
      renderAuthorsPage();
    }
  });
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
  console.log('Loaded papers:', papers.length);
  const allTags = new Set(papers.flatMap(p=>p.tags||[]));
  const allAuthors = new Set(papers.flatMap(p=>(p.authorships||[]).map(a=>a.name).filter(Boolean)));
  
  // グローバル変数にデータを保存
  window.allPapers = papers;
  window.allStats = stats;
  
  renderCounters(stats);
  renderCharts(stats);
  renderTopAuthors(stats, papers);
  setupPagination();
  
  // 初期表示
  refresh();
  
  // 初期状態でフィルターを閉じる
  closeAllFilters();

  const tagContainer = mountTagFilter(allTags, stats);
  const authorContainer = mountAuthorFilter(allAuthors, stats);
  const list = document.getElementById('list');
  const clear = document.getElementById('clear');
  const clearAuthors = document.getElementById('clear-authors');
  let currentSort = 'citations'; // デフォルトは被引用数順

  function refresh(){
    const selectedTags = new Set();
    tagContainer.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
      selectedTags.add(cb.value);
    });
    
    const selectedAuthors = new Set();
    authorContainer.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
      selectedAuthors.add(cb.value);
    });
    
    const view = filterPapers(papers, selectedTags, selectedAuthors, currentSort);
    console.log('Filtered papers:', view.length, 'Total papers:', papers.length);
    list.innerHTML = '';
    for(const w of view){ list.appendChild(renderCard(w)); }
  }
  
  // グローバルに公開（著者フィルター機能で使用）
  window.refreshPapers = refresh;

  tagContainer.addEventListener('change', refresh);
  clear.addEventListener('click', ()=>{ 
    tagContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false); 
    refresh(); 
  });
  
  authorContainer.addEventListener('change', refresh);
  clearAuthors.addEventListener('click', ()=>{ 
    authorContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false); 
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

  // 著者フィルター開閉機能
  const authorFilterToggle = document.getElementById('author-filter-toggle');
  const authorFilterContent = document.getElementById('author-filter-content');
  const authorToggleIcon = authorFilterToggle.querySelector('.toggle-icon');

  authorFilterToggle.addEventListener('click', () => {
    const isCollapsed = authorFilterContent.classList.contains('collapsed');
    if (isCollapsed) {
      authorFilterContent.classList.remove('collapsed');
      authorFilterContent.classList.add('expanded');
      authorToggleIcon.style.transform = 'rotate(180deg)';
    } else {
      authorFilterContent.classList.remove('expanded');
      authorFilterContent.classList.add('collapsed');
      authorToggleIcon.style.transform = 'rotate(0deg)';
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