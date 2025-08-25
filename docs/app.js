async function loadJSON(path){
  // キャッシュを回避するためにタイムスタンプを追加
  const timestamp = new Date().getTime();
  const url = path.includes('?') ? `${path}&t=${timestamp}` : `${path}?t=${timestamp}`;
  const r = await fetch(url);
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
  const authors = (w.authorships||[]).map(a=>a.name).filter(Boolean);
  const authorCount = authors.length;
  const maxAuthorsToShow = 3; // 最初に表示する著者数
  
  let authorDisplay;
  if (authorCount === 0) {
    authorDisplay = '(authors unknown)';
  } else if (authorCount <= maxAuthorsToShow) {
    authorDisplay = authors.join(', ');
  } else {
    const firstAuthors = authors.slice(0, maxAuthorsToShow).join(', ');
    const remainingCount = authorCount - maxAuthorsToShow;
    authorDisplay = `${firstAuthors} +${remainingCount} more`;
  }
  
  const url = w.landing_page_url || (w.doi ? `https://doi.org/${w.doi.replace('https://doi.org/','')}` : null);
  const tags = (w.tags||[]).map(t=>el('span',{class:'tag'}, t));
  
  return el('article', {class:'card'},
    el('h3',{}, w.title||'(no title)'),
    el('div',{class:'meta'}, [authorDisplay,' • ', w.host_venue||'(venue unknown)',' • ', w.publication_year||'–'].filter(Boolean).join(' ')),
    el('div',{class:'citation-count'}, `被引用数: ${w.cited_by_count || 0}`),
    el('div',{class:'tags'}, ...tags),
    url ? el('a',{class:'btn', href:url, target:'_blank', rel:'noopener'}, 'Open') : null
  );
}

function filterPapers(papers, selectedTags, selectedAuthors, selectedVenues, sortBy = 'citations'){
  const filtered = papers.filter(w=>{
    // AND検索: 選択された全てのタグが含まれている必要がある
    const okTag = !selectedTags.size || selectedTags.size === 0 || 
                  Array.from(selectedTags).every(tag => (w.tags||[]).includes(tag));
    
    // AND検索: 選択された全ての著者が含まれている必要がある
    const paperAuthors = (w.authorships||[]).map(a=>a.name).filter(Boolean);
    const okAuthor = !selectedAuthors.size || selectedAuthors.size === 0 || 
                     Array.from(selectedAuthors).every(author => paperAuthors.includes(author));
    
    // OR検索: 選択された学会・ジャーナルのいずれかに含まれていればOK
    const paperVenue = w.host_venue || 'Unknown';
    const okVenue = !selectedVenues.size || selectedVenues.size === 0 || 
                    Array.from(selectedVenues).some(venueGroup => {
                      // venueGroupは|で区切られた複数の学会名
                      const venues = venueGroup.split('|');
                      return venues.includes(paperVenue);
                    });
    
    return okTag && okAuthor && okVenue;
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

function mountVenueFilter(allVenues, stats){
  const container = document.getElementById('venue-checkboxes');
  container.innerHTML = '';
  
  // 学会・ジャーナルの論文数を取得する関数
  const getVenuePaperCount = (venueName) => {
    return stats.by_venue ? stats.by_venue[venueName] || 0 : 0;
  };
  
  // 学会名を正規化する関数（年を除去して同じ学会をまとめる）
  const normalizeVenueName = (venueName) => {
    // 年を含むパターンを除去
    const normalized = venueName
      .replace(/\d{4}\s+(IEEE|ACM|International|Conference|Symposium)/gi, '$1')
      .replace(/\d{4}\s*[-–]\s*\d{4}/g, '') // 年範囲を除去
      .replace(/\d{4}/g, '') // 単独の年を除去
      .replace(/\s+/g, ' ') // 複数の空白を単一の空白に
      .trim();
    
    // 略称を抽出
    const abbreviation = extractAbbreviation(venueName);
    
    return { normalized, abbreviation };
  };
  
  // 略称を抽出する関数
  const extractAbbreviation = (venueName) => {
    // 括弧内の略称を抽出
    const match = venueName.match(/\(([A-Z]{2,})\)/);
    if (match) {
      return match[1];
    }
    
    // 一般的な略称パターンを抽出
    const patterns = [
      { pattern: /Proceedings of the VLDB Endowment/i, abbr: 'PVLDB' },
      { pattern: /Proceedings of the ACM on Management of Data/i, abbr: 'SIGMOD' },
      { pattern: /Proceedings of the International Conference on Management of Data/i, abbr: 'SIGMOD' },
      { pattern: /IEEE International Conference on Data Engineering/i, abbr: 'ICDE' },
      { pattern: /Conference on Innovative Data Systems Research/i, abbr: 'CIDR' },
      { pattern: /IEEE Transactions on Knowledge and Data Engineering/i, abbr: 'TKDE' },
      { pattern: /The VLDB Journal/i, abbr: 'VLDBJ' },
      { pattern: /ACM Transactions on Storage/i, abbr: 'TOS' },
      { pattern: /Proceedings of the AAAI Conference on Artificial Intelligence/i, abbr: 'AAAI' },
      { pattern: /International Conference on Learning Representations/i, abbr: 'ICLR' },
      { pattern: /IEEE Transactions on Parallel and Distributed Systems/i, abbr: 'TPDS' },
      { pattern: /IEEE Communications Surveys & Tutorials/i, abbr: 'COMST' },
      { pattern: /ACM Computing Surveys/i, abbr: 'CSUR' },
      { pattern: /Journal of the ACM/i, abbr: 'JACM' },
      { pattern: /Communications of the ACM/i, abbr: 'CACM' },
      { pattern: /ACM Transactions on Graphics/i, abbr: 'TOG' },
      { pattern: /IEEE Transactions on Pattern Analysis and Machine Intelligence/i, abbr: 'TPAMI' },
      { pattern: /Proceedings of the ACM Web Conference/i, abbr: 'WWW' },
      { pattern: /Neural Information Processing Systems/i, abbr: 'NeurIPS' },
      { pattern: /International Conference on Machine Learning/i, abbr: 'ICML' },
      { pattern: /IEEE International Solid-State Circuits Conference/i, abbr: 'ISSCC' },
      { pattern: /International Journal of Geographical Information Science/i, abbr: 'IJGIS' },
      { pattern: /IEEE Transactions on Network and Service Management/i, abbr: 'TNSM' },
      { pattern: /Distributed and Parallel Databases/i, abbr: 'DPD' },
      { pattern: /Knowledge and Information Systems/i, abbr: 'KAIS' },
      { pattern: /The Journal of Supercomputing/i, abbr: 'JSC' },
      { pattern: /Information Processing & Management/i, abbr: 'IPM' },
      { pattern: /Data Science and Engineering/i, abbr: 'DSE' },
      { pattern: /Nucleic Acids Research/i, abbr: 'NAR' },
      { pattern: /Nature Computational Science/i, abbr: 'NCS' },
      { pattern: /Cell Genomics/i, abbr: 'CG' },
      { pattern: /Bioinformatics/i, abbr: 'BIO' },
      { pattern: /Artificial Intelligence Review/i, abbr: 'AIR' },
      { pattern: /Information Sciences/i, abbr: 'IS' },
      { pattern: /Applied Sciences/i, abbr: 'AS' },
      { pattern: /Electronics/i, abbr: 'EL' },
      { pattern: /Synthesis lectures on data management/i, abbr: 'SLDM' },
      { pattern: /Communications in computer and information science/i, abbr: 'CCIS' },
      { pattern: /Lecture notes in computer science/i, abbr: 'LNCS' },
      { pattern: /IEEE Data\(base\) Engineering Bulletin/i, abbr: 'DEB' },
      { pattern: /ACM SIGMOD Record/i, abbr: 'SIGMOD Record' },
      { pattern: /IEEE Access/i, abbr: 'Access' },
      { pattern: /arXiv \(Cornell University\)/i, abbr: 'arXiv' },
      { pattern: /bioRxiv \(Cold Spring Harbor Laboratory\)/i, abbr: 'bioRxiv' },
      { pattern: /Chapman and Hall\/CRC eBooks/i, abbr: 'CRC' },
      { pattern: /Daedalus/i, abbr: 'Daedalus' },
      { pattern: /Computer Communications/i, abbr: 'CC' },
      { pattern: /Discrete Optimization/i, abbr: 'DO' },
      { pattern: /International Journal of Scientific Research in Science Engineering and Technology/i, abbr: 'IJSRET' }
    ];
    
    for (const { pattern, abbr } of patterns) {
      if (pattern.test(venueName)) {
        return abbr;
      }
    }
    
    return null;
  };
  
  // 学会名を正規化してグループ化
  const venueGroups = {};
  [...allVenues].forEach(venue => {
    const count = getVenuePaperCount(venue);
    if (count > 0) { // 0論文の学会を除外
      const { normalized, abbreviation } = normalizeVenueName(venue);
      const key = normalized;
      if (!venueGroups[key]) {
        venueGroups[key] = { 
          count: 0, 
          originalNames: [], 
          abbreviation: abbreviation 
        };
      }
      venueGroups[key].count += count;
      venueGroups[key].originalNames.push(venue);
      // 略称が複数ある場合は最初のものを保持
      if (!venueGroups[key].abbreviation && abbreviation) {
        venueGroups[key].abbreviation = abbreviation;
      }
    }
  });
  
  // 論文数の多い順にソート
  const sortedVenues = Object.entries(venueGroups)
    .sort(([,a], [,b]) => b.count - a.count);
  
  sortedVenues.forEach(([normalizedName, data]) => {
    // 略称を含めた表示名を作成
    const displayName = data.abbreviation 
      ? `${normalizedName} (${data.abbreviation})`
      : normalizedName;
    
    const label = el('label', {class: 'venue-checkbox'}, 
      el('input', {type: 'checkbox', value: data.originalNames.join('|')}), // 元の名前を|で結合
      el('span', {class: 'venue-text'}, `${displayName} (${data.count} papers)`)
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
  if (filterContent && toggleIcon) {
    filterContent.classList.remove('expanded');
    filterContent.classList.add('collapsed');
    toggleIcon.style.transform = 'rotate(0deg)';
  }
  
  // 著者フィルターを閉じる
  const authorFilterContent = document.getElementById('author-filter-content');
  const authorToggleIcon = document.querySelector('#author-filter-toggle .toggle-icon');
  if (authorFilterContent && authorToggleIcon) {
    authorFilterContent.classList.remove('expanded');
    authorFilterContent.classList.add('collapsed');
    authorToggleIcon.style.transform = 'rotate(0deg)';
  }
  
  // 学会フィルターを閉じる
  const venueFilterContent = document.getElementById('venue-filter-content');
  const venueToggleIcon = document.querySelector('#venue-filter-toggle .toggle-icon');
  if (venueFilterContent && venueToggleIcon) {
    venueFilterContent.classList.remove('expanded');
    venueFilterContent.classList.add('collapsed');
    venueToggleIcon.style.transform = 'rotate(0deg)';
  }
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

function getAuthorInstitutionsWithYears(authorName, papers, stats) {
  // まず統計データから所属情報を取得
  const topAuthor = stats.top_authors?.find(a => a.name === authorName);
  if (topAuthor && topAuthor.institution_years) {
    return Object.entries(topAuthor.institution_years).map(([institution, data]) => ({
      name: institution,
      yearRange: data.year_range,
      years: data.years
    }));
  }
  
  // 統計データにない場合は論文データから取得
  const institutionYears = {};
  papers.forEach(paper => {
    const year = paper.publication_year;
    (paper.authorships || []).forEach(authorship => {
      if (authorship.name === authorName && authorship.institutions && year) {
        authorship.institutions.forEach(inst => {
          if (!institutionYears[inst]) {
            institutionYears[inst] = new Set();
          }
          institutionYears[inst].add(year);
        });
      }
    });
  });
  
  return Object.entries(institutionYears).map(([institution, years]) => {
    const yearArray = Array.from(years).sort();
    return {
      name: institution,
      yearRange: `${Math.min(...yearArray)}-${Math.max(...yearArray)}`,
      years: yearArray
    };
  });
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
    
    // 著者の所属を取得（年次情報付き）
    const institutionsWithYears = getAuthorInstitutionsWithYears(name, window.allPapers || [], window.allStats || {});
    const institutionText = institutionsWithYears.length > 0 
      ? ` (${institutionsWithYears.map(inst => `${inst.name} (${inst.yearRange})`).join(', ')})` 
      : '';
    
    // デバッグ用（Tim Kraskaの場合）
    if (name === 'Tim Kraska') {
      console.log('Tim Kraska institutions with years:', institutionsWithYears);
      console.log('Tim Kraska stats data:', window.allStats?.top_authors?.find(a => a.name === 'Tim Kraska'));
    }
    
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
        el('div', {class: 'author-name', onclick: `filterByAuthor('${name}')`}, name + institutionText)
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
  console.log('Loading data...');
  const citations = await loadJSON('data/citations.json');
  console.log('Citations loaded');
  const stats = await loadJSON('data/stats.json');
  console.log('Stats loaded');

  const papers = citations.results||[];
  console.log('Loaded papers:', papers.length);
  console.log('Stats data loaded:', !!stats);
  console.log('Stats keys:', Object.keys(stats || {}));
  console.log('Top authors count:', stats.top_authors?.length || 0);
  if (stats.top_authors) {
    const timKraska = stats.top_authors.find(a => a.name === 'Tim Kraska');
    console.log('Tim Kraska in stats:', timKraska);
    if (timKraska) {
      console.log('Tim Kraska institutions:', timKraska.institutions);
    }
  }
  const allTags = new Set(papers.flatMap(p=>p.tags||[]));
  const allAuthors = new Set(papers.flatMap(p=>(p.authorships||[]).map(a=>a.name).filter(Boolean)));
  const allVenues = new Set(papers.map(p=>p.host_venue||'Unknown').filter(Boolean));
  
  // グローバル変数にデータを保存
  window.allPapers = papers;
  window.allStats = stats;
  
  renderCounters(stats);
  renderCharts(stats);
  renderTopAuthors(stats, papers);
  setupPagination();

  const tagContainer = mountTagFilter(allTags, stats);
  const authorContainer = mountAuthorFilter(allAuthors, stats);
  const venueContainer = mountVenueFilter(allVenues, stats);
  const list = document.getElementById('list');
  const clear = document.getElementById('clear');
  const clearAuthors = document.getElementById('clear-authors');
  const clearVenues = document.getElementById('clear-venues');
  let currentSort = 'citations'; // デフォルトは被引用数順

  function refresh(){
    console.log('refresh() called');
    console.log('tagContainer:', tagContainer);
    console.log('authorContainer:', authorContainer);
    console.log('venueContainer:', venueContainer);
    
    const selectedTags = new Set();
    if (tagContainer) {
      tagContainer.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
        selectedTags.add(cb.value);
      });
    }
    
    const selectedAuthors = new Set();
    if (authorContainer) {
      authorContainer.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
        selectedAuthors.add(cb.value);
      });
    }
    
    const selectedVenues = new Set();
    if (venueContainer) {
      venueContainer.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
        selectedVenues.add(cb.value);
      });
    }
    
    console.log('Selected tags:', selectedTags.size);
    console.log('Selected authors:', selectedAuthors.size);
    console.log('Selected venues:', selectedVenues.size);
    
    const view = filterPapers(papers, selectedTags, selectedAuthors, selectedVenues, currentSort);
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
  
  venueContainer.addEventListener('change', refresh);
  clearVenues.addEventListener('click', ()=>{ 
    venueContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false); 
    refresh(); 
  });
  
  // 全ての絞り込みをクリアするボタン
  const clearAllFilters = document.getElementById('clear-all-filters');
  clearAllFilters.addEventListener('click', () => {
    // 全てのチェックボックスをクリア
    tagContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    authorContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    venueContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    refresh();
  });
  
  // 初期状態でフィルターを閉じる
  closeAllFilters();
  
  // 初期表示
  refresh();

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

  // 学会フィルター開閉機能
  const venueFilterToggle = document.getElementById('venue-filter-toggle');
  const venueFilterContent = document.getElementById('venue-filter-content');
  const venueToggleIcon = venueFilterToggle.querySelector('.toggle-icon');

  venueFilterToggle.addEventListener('click', () => {
    const isCollapsed = venueFilterContent.classList.contains('collapsed');
    if (isCollapsed) {
      venueFilterContent.classList.remove('collapsed');
      venueFilterContent.classList.add('expanded');
      venueToggleIcon.style.transform = 'rotate(180deg)';
    } else {
      venueFilterContent.classList.remove('expanded');
      venueFilterContent.classList.add('collapsed');
      venueToggleIcon.style.transform = 'rotate(0deg)';
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