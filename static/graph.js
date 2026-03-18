/* SkillGrowthNavigator - D3 Directed Graph + App Logic */

const DOMAIN_COLORS = {
  backend: '#58a6ff',
  frontend: '#f97583',
  devops: '#56d364',
  data: '#d2a8ff',
  security: '#e3b341',
};

const LEVEL_RADIUS = { beginner: 10, intermediate: 14, advanced: 18 };

const CAREER_GOAL_DESC = {};

/* ── State ─────────────────────────────────────────────────────────── */

let graphData = { nodes: [], edges: [] };
let allSkills = {};
let userSkills = new Set();
let recommendations = [];
let simulation = null;
let svg = null;
let nodeElements = null;
let linkElements = null;
let labelElements = null;

/* ── Init ──────────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', async () => {
  const [graphResp, skillsResp, goalsResp] = await Promise.all([
    fetch('/api/graph').then(r => r.json()),
    fetch('/api/skills').then(r => r.json()),
    fetch('/api/goals').then(r => r.json()),
  ]);
  graphData = graphResp;
  allSkills = skillsResp;
  Object.entries(goalsResp).forEach(([id, g]) => {
    CAREER_GOAL_DESC[id] = g.description;
  });
  renderGraph();
  updateRecommendations();
});

/* ── Graph Rendering ───────────────────────────────────────────────── */

function renderGraph() {
  const container = document.getElementById('graph-container');
  const width = container.clientWidth || 800;
  const height = 450;

  d3.select('#graph-container').selectAll('*').remove();

  svg = d3.select('#graph-container')
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', [0, 0, width, height]);

  // Zoom
  const g = svg.append('g');
  svg.call(d3.zoom()
    .scaleExtent([0.3, 3])
    .on('zoom', (event) => g.attr('transform', event.transform)));

  // Arrow marker
  svg.append('defs').append('marker')
    .attr('id', 'arrow')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 22)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#30363d');

  // Links
  linkElements = g.append('g')
    .selectAll('line')
    .data(graphData.edges)
    .join('line')
    .attr('stroke', '#30363d')
    .attr('stroke-width', 1.5)
    .attr('marker-end', 'url(#arrow)');

  // Nodes
  nodeElements = g.append('g')
    .selectAll('circle')
    .data(graphData.nodes)
    .join('circle')
    .attr('r', d => LEVEL_RADIUS[d.level])
    .attr('fill', d => DOMAIN_COLORS[d.domain])
    .attr('stroke', '#0d1117')
    .attr('stroke-width', 2)
    .attr('opacity', 0.7)
    .attr('cursor', 'pointer')
    .on('click', (event, d) => showSkillDetail(d.id))
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended));

  // Tooltips
  nodeElements.append('title').text(d => d.name);

  // Labels
  labelElements = g.append('g')
    .selectAll('text')
    .data(graphData.nodes)
    .join('text')
    .text(d => d.name)
    .attr('font-size', 8)
    .attr('fill', '#8b949e')
    .attr('text-anchor', 'middle')
    .attr('dy', d => LEVEL_RADIUS[d.level] + 12)
    .attr('pointer-events', 'none');

  // Simulation
  simulation = d3.forceSimulation(graphData.nodes)
    .force('link', d3.forceLink(graphData.edges).id(d => d.id).distance(100))
    .force('charge', d3.forceManyBody().strength(-250))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => LEVEL_RADIUS[d.level] + 8))
    .force('x', d3.forceX(width / 2).strength(0.05))
    .force('y', d3.forceY(height / 2).strength(0.05));

  simulation.on('tick', () => {
    linkElements
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);
    nodeElements
      .attr('cx', d => d.x)
      .attr('cy', d => d.y);
    labelElements
      .attr('x', d => d.x)
      .attr('y', d => d.y);
  });
}

function dragstarted(event) {
  if (!event.active) simulation.alphaTarget(0.3).restart();
  event.subject.fx = event.subject.x;
  event.subject.fy = event.subject.y;
}

function dragged(event) {
  event.subject.fx = event.x;
  event.subject.fy = event.y;
}

function dragended(event) {
  if (!event.active) simulation.alphaTarget(0);
  event.subject.fx = null;
  event.subject.fy = null;
}

/* ── Graph Highlights ──────────────────────────────────────────────── */

function updateGraphHighlights() {
  if (!nodeElements) return;
  const recIds = new Set(recommendations.map(r => r.id));

  nodeElements
    .attr('opacity', d => {
      if (userSkills.has(d.id)) return 1.0;
      if (recIds.has(d.id)) return 0.9;
      return 0.35;
    })
    .attr('stroke', d => {
      if (userSkills.has(d.id)) return '#ffffff';
      if (recIds.has(d.id)) return DOMAIN_COLORS[d.domain];
      return '#0d1117';
    })
    .attr('stroke-width', d => {
      if (userSkills.has(d.id)) return 3;
      if (recIds.has(d.id)) return 3;
      return 2;
    })
    .classed('node-acquired', d => userSkills.has(d.id))
    .classed('node-recommended', d => recIds.has(d.id));

  linkElements
    .attr('stroke', d => {
      const srcId = typeof d.source === 'object' ? d.source.id : d.source;
      const tgtId = typeof d.target === 'object' ? d.target.id : d.target;
      if (userSkills.has(srcId) && recIds.has(tgtId)) return DOMAIN_COLORS[allSkills[tgtId]?.domain] || '#30363d';
      if (userSkills.has(srcId) && userSkills.has(tgtId)) return '#484f58';
      return '#30363d';
    })
    .attr('stroke-width', d => {
      const srcId = typeof d.source === 'object' ? d.source.id : d.source;
      const tgtId = typeof d.target === 'object' ? d.target.id : d.target;
      if (userSkills.has(srcId) && recIds.has(tgtId)) return 2.5;
      return 1.5;
    });

  labelElements
    .attr('fill', d => {
      if (userSkills.has(d.id)) return '#c9d1d9';
      if (recIds.has(d.id)) return '#c9d1d9';
      return '#484f58';
    });
}

/* ── Recommendations ───────────────────────────────────────────────── */

async function updateRecommendations() {
  const goal = document.getElementById('career-goal').value;
  const skills = Array.from(userSkills);

  const resp = await fetch('/api/recommend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skills, career_goal: goal }),
  });
  recommendations = await resp.json();

  renderRecommendations();
  updateGraphHighlights();
  updateSkillCount();
}

function renderRecommendations() {
  const container = document.getElementById('recommendations');
  const hoursEl = document.getElementById('rec-hours');

  if (recommendations.length === 0) {
    container.innerHTML = '<p class="empty-state">No recommendations available. Select a career goal or adjust your skills.</p>';
    hoursEl.textContent = '';
    return;
  }

  const totalHours = recommendations.reduce((sum, r) => sum + r.estimated_hours, 0);
  hoursEl.textContent = totalHours + 'h total';

  container.innerHTML = recommendations.map(rec => `
    <div class="rec-card" style="border-left: 3px solid ${DOMAIN_COLORS[rec.domain]}" onclick="showSkillDetail('${rec.id}')">
      <div class="rec-header">
        <strong>${esc(rec.name)}</strong>
        <span class="level-badge level-${rec.level}">${rec.level}</span>
        <span class="domain-tag" style="color:${DOMAIN_COLORS[rec.domain]}">${rec.domain}</span>
      </div>
      <div class="rec-meta">
        <span>${rec.estimated_hours}h estimated</span>
        <span>Relevance: ${Math.round(rec.score * 100)}%</span>
      </div>
      ${rec.prerequisites.length ? `<div class="rec-prereqs">Prereqs: ${rec.prerequisites.map(p => esc(allSkills[p]?.name || p)).join(', ')}</div>` : ''}
      <div class="rec-resources">
        ${rec.resources.map(r => `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>`).join('')}
      </div>
    </div>
  `).join('');
}

/* ── Skill Detail Panel ────────────────────────────────────────────── */

function showSkillDetail(skillId) {
  const skill = allSkills[skillId];
  if (!skill) return;

  const panel = document.getElementById('skill-detail');
  panel.style.display = 'block';

  document.getElementById('detail-name').textContent = skill.name;

  const domainEl = document.getElementById('detail-domain');
  domainEl.textContent = skill.domain;
  domainEl.style.color = DOMAIN_COLORS[skill.domain];

  const levelEl = document.getElementById('detail-level');
  levelEl.textContent = skill.level;
  levelEl.className = 'level-badge level-' + skill.level;

  document.getElementById('detail-hours').textContent = skill.estimated_hours + ' hours';

  const prereqEl = document.getElementById('detail-prereqs');
  if (skill.prerequisites.length) {
    prereqEl.innerHTML = '<strong>Prerequisites:</strong> ' +
      skill.prerequisites.map(p => esc(allSkills[p]?.name || p)).join(', ');
  } else {
    prereqEl.innerHTML = '<strong>Prerequisites:</strong> None';
  }

  const resList = document.getElementById('detail-resources');
  resList.innerHTML = skill.resources.map(r =>
    `<li><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a></li>`
  ).join('');
}

/* ── Event Handlers ────────────────────────────────────────────────── */

function onSelectionChange() {
  // Update userSkills from checkboxes
  userSkills.clear();
  document.querySelectorAll('.skill-checkbox:checked').forEach(cb => {
    userSkills.add(cb.value);
  });

  // Update goal description
  const goalSelect = document.getElementById('career-goal');
  const descEl = document.getElementById('goal-description');
  descEl.textContent = CAREER_GOAL_DESC[goalSelect.value] || '';

  updateRecommendations();
}

function updateSkillCount() {
  document.getElementById('skill-count').textContent = userSkills.size + ' / 30';
}

/* ── Profile Save/Load ─────────────────────────────────────────────── */

async function saveProfile() {
  const username = document.getElementById('username').value.trim();
  if (!username) {
    showToast('Enter a username first', 'error');
    return;
  }

  const resp = await fetch('/api/profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username,
      career_goal: document.getElementById('career-goal').value,
      skills: Array.from(userSkills),
    }),
  });

  if (resp.ok) {
    showToast('Profile saved', 'success');
  } else {
    showToast('Failed to save profile', 'error');
  }
}

async function loadProfile() {
  const username = document.getElementById('username').value.trim();
  if (!username) {
    showToast('Enter a username first', 'error');
    return;
  }

  const resp = await fetch('/api/profile?username=' + encodeURIComponent(username));
  if (!resp.ok) {
    showToast('Failed to load profile', 'error');
    return;
  }

  const data = await resp.json();
  if (data.error) {
    showToast(data.error, 'error');
    return;
  }

  // Set career goal
  document.getElementById('career-goal').value = data.career_goal || '';

  // Set skill checkboxes
  document.querySelectorAll('.skill-checkbox').forEach(cb => {
    cb.checked = data.skills.includes(cb.value);
  });

  // Trigger update
  onSelectionChange();
  showToast('Profile loaded', 'success');
}

/* ── Utilities ─────────────────────────────────────────────────────── */

function esc(str) {
  const el = document.createElement('span');
  el.textContent = str;
  return el.innerHTML;
}

function showToast(message, type) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast ' + (type || '');
  toast.textContent = message;
  document.body.appendChild(toast);

  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 2500);
}
