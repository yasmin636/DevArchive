let archives = JSON.parse(localStorage.getItem('ud_archives') || '[]');
let deleteTargetId = null;
let editingId = null;

const archModal   = new bootstrap.Modal(document.getElementById('archModal'));
const deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
const viewModal   = new bootstrap.Modal(document.getElementById('viewModal'));
const toastEl     = document.getElementById('appToast');
const bsToast     = new bootstrap.Toast(toastEl, { delay: 3000 });

function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
}

function showToast(msg, type) {
  toastEl.className = 'toast align-items-center text-white border-0 bg-' + (type === 'danger' ? 'danger' : 'success');
  document.getElementById('toastMsg').textContent = msg;
  bsToast.show();
}

function persist() {
  localStorage.setItem('ud_archives', JSON.stringify(archives));
  updateStats();
  buildAnneeFilter();
  renderTable();
}

function updateStats() {
  const cc    = archives.filter(a => a.type === 'CC').length;
  const exam  = archives.filter(a => a.type === 'Examen Final').length;
  const years = [...new Set(archives.map(a => a.annee))].sort().reverse();
  document.getElementById('stat-total').textContent      = archives.length;
  document.getElementById('stat-cc').textContent         = cc;
  document.getElementById('stat-exam').textContent       = exam;
  document.getElementById('stat-annee').textContent      = years[0] || '—';
  document.getElementById('nav-cc-count').textContent    = cc;
  document.getElementById('nav-exam-count').textContent  = exam;
  document.getElementById('nav-total-count').textContent = archives.length;
}

function buildAnneeFilter() {
  const sel   = document.getElementById('filterAnnee');
  const cur   = sel.value;
  const years = [...new Set(archives.map(a => a.annee).filter(Boolean))].sort().reverse();
  sel.innerHTML = '<option value="">Toutes les années</option>';
  years.forEach(y => {
    const opt = document.createElement('option');
    opt.value = y;
    opt.textContent = y.replace('-', ' – ');
    if (y === cur) opt.selected = true;
    sel.appendChild(opt);
  });
}

function renderTable() {
  const search = document.getElementById('searchInput').value.toLowerCase();
  const fType  = document.getElementById('filterType').value;
  const fAnnee = document.getElementById('filterAnnee').value;

  const filtered = archives.filter(a => {
    const matchS = a.title.toLowerCase().includes(search)   ||
                   a.module.toLowerCase().includes(search)  ||
                   a.filiere.toLowerCase().includes(search);
    return matchS && (!fType || a.type === fType) && (!fAnnee || a.annee === fAnnee);
  });

  document.getElementById('count-badge').textContent = filtered.length;
  const tbody = document.getElementById('archTableBody');
  const empty = document.getElementById('emptyState');

  if (filtered.length === 0) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  tbody.innerHTML = filtered.map((a, i) => `
    <tr>
      <td class="text-muted" style="font-size:.75rem;">${String(i + 1).padStart(2, '0')}</td>
      <td>
        <div style="font-weight:600;font-size:.85rem;">${a.title}</div>
        ${a.remarque ? `<small class="text-muted">${a.remarque}</small>` : ''}
      </td>
      <td>${a.type === 'CC' ? '<span class="badge-cc">CC</span>' : '<span class="badge-exam">Examen Final</span>'}</td>
      <td style="font-size:.82rem;">${a.module}</td>
      <td style="font-size:.82rem;">${a.filiere}</td>
      <td><span class="badge-annee">${a.annee ? a.annee.replace('-', ' – ') : '—'}</span></td>
      <td style="font-size:.82rem;">${a.session || '—'}${a.semestre ? ' · ' + a.semestre : ''}</td>
      <td style="font-size:.82rem;white-space:nowrap;">${a.dateArchive}</td>
      <td>
        <button class="action-btn view"  data-action="view"   data-id="${a.id}" title="Voir"><i class="bi bi-eye"></i></button>
        <button class="action-btn edit"  data-action="edit"   data-id="${a.id}" title="Modifier"><i class="bi bi-pencil"></i></button>
        <button class="action-btn del"   data-action="delete" data-id="${a.id}" title="Supprimer"><i class="bi bi-trash3"></i></button>
      </td>
    </tr>
  `).join('');
}

function applyFilter(type) {
  document.getElementById('filterType').value = type;
  renderTable();
}

function selectType(type) {
  document.getElementById('archType').value     = type;
  document.getElementById('typeCC').className   = 'type-card' + (type === 'CC'           ? ' selected-cc'   : '');
  document.getElementById('typeExam').className = 'type-card' + (type === 'Examen Final' ? ' selected-exam' : '');
  document.getElementById('typeError').textContent = '';
}

function openAddModal() {
  editingId = null;
  document.getElementById('archModalTitle').innerHTML = '<i class="bi bi-archive me-2 text-primary"></i>Archiver un document';
  document.getElementById('archForm').reset();
  document.getElementById('archId').value           = '';
  document.getElementById('archType').value         = '';
  document.getElementById('typeCC').className       = 'type-card';
  document.getElementById('typeExam').className     = 'type-card';
  document.getElementById('typeError').textContent  = '';
  archModal.show();
}

function saveArchive() {
  const type     = document.getElementById('archType').value;
  const title    = document.getElementById('archTitle').value.trim();
  const module   = document.getElementById('archModule').value.trim();
  const filiere  = document.getElementById('archFiliere').value.trim();
  const annee    = document.getElementById('archAnnee').value;
  const session  = document.getElementById('archSession').value;
  const semestre = document.getElementById('archSemestre').value;
  const remarque = document.getElementById('archRemarque').value.trim();

  if (!type) {
    document.getElementById('typeError').textContent = 'Sélectionnez un type.';
    return;
  }
  if (!title || !module || !filiere || !annee) {
    showToast('Veuillez remplir tous les champs obligatoires.', 'danger');
    return;
  }

  const today = new Date().toLocaleDateString('fr-FR');

  if (editingId) {
    const idx = archives.findIndex(a => a.id === editingId);
    archives[idx] = { ...archives[idx], type, title, module, filiere, annee, session, semestre, remarque };
    showToast('Archive modifiée avec succès.', 'success');
  } else {
    archives.unshift({ id: uid(), type, title, module, filiere, annee, session, semestre, remarque, dateArchive: today });
    showToast('Document archivé avec succès.', 'success');
  }

  persist();
  archModal.hide();
}

function editArchive(id) {
  const a = archives.find(x => x.id === id);
  if (!a) return;
  editingId = id;
  document.getElementById('archModalTitle').innerHTML  = '<i class="bi bi-pencil me-2 text-warning"></i>Modifier l\'archive';
  document.getElementById('archId').value       = a.id;
  document.getElementById('archTitle').value    = a.title;
  document.getElementById('archModule').value   = a.module;
  document.getElementById('archFiliere').value  = a.filiere;
  document.getElementById('archAnnee').value    = a.annee;
  document.getElementById('archSession').value  = a.session;
  document.getElementById('archSemestre').value = a.semestre;
  document.getElementById('archRemarque').value = a.remarque || '';
  selectType(a.type);
  archModal.show();
}

function viewArchive(id) {
  const a = archives.find(x => x.id === id);
  if (!a) return;
  const badge = a.type === 'CC'
    ? '<span class="badge-cc">Contrôle Continu</span>'
    : '<span class="badge-exam">Examen Final</span>';
  document.getElementById('viewModalBody').innerHTML = `
    <div class="d-flex justify-content-between align-items-start mb-3">
      <h6 style="font-weight:700;font-size:1rem;margin:0;">${a.title}</h6>
      ${badge}
    </div>
    <table class="table table-sm table-borderless" style="font-size:.85rem;">
      <tr><td class="text-muted fw-semibold" style="width:140px;">Module</td><td>${a.module}</td></tr>
      <tr><td class="text-muted fw-semibold">Filière</td><td>${a.filiere}</td></tr>
      <tr><td class="text-muted fw-semibold">Année univ.</td><td>${a.annee ? a.annee.replace('-', ' – ') : '—'}</td></tr>
      <tr><td class="text-muted fw-semibold">Session</td><td>${a.session || '—'}</td></tr>
      <tr><td class="text-muted fw-semibold">Semestre</td><td>${a.semestre || '—'}</td></tr>
      <tr><td class="text-muted fw-semibold">Archivé le</td><td>${a.dateArchive}</td></tr>
      ${a.remarque ? `<tr><td class="text-muted fw-semibold">Remarques</td><td>${a.remarque}</td></tr>` : ''}
    </table>
  `;
  viewModal.show();
}

function confirmDelete(id) {
  const a = archives.find(x => x.id === id);
  if (!a) return;
  deleteTargetId = id;
  document.getElementById('deleteItemName').textContent = a.title;
  document.getElementById('deleteItemMeta').textContent =
    (a.type === 'CC' ? 'Contrôle Continu' : 'Examen Final') +
    ' · ' + (a.annee || '') + ' · ' + (a.filiere || '');
  deleteModal.show();
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('show');
}

function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('overlay').classList.remove('show');
}

document.getElementById('sidebarToggle').addEventListener('click', toggleSidebar);
document.getElementById('overlay').addEventListener('click', closeSidebar);

document.getElementById('navCC').addEventListener('click', function (e) {
  e.preventDefault();
  applyFilter('CC');
});
document.getElementById('navExam').addEventListener('click', function (e) {
  e.preventDefault();
  applyFilter('Examen Final');
});
document.getElementById('navAll').addEventListener('click', function (e) {
  e.preventDefault();
  applyFilter('');
});

document.getElementById('btnOpenAddModal').addEventListener('click', openAddModal);

document.getElementById('searchInput').addEventListener('input', renderTable);
document.getElementById('filterType').addEventListener('change', renderTable);
document.getElementById('filterAnnee').addEventListener('change', renderTable);

document.getElementById('typeCC').addEventListener('click', function () { selectType('CC'); });
document.getElementById('typeExam').addEventListener('click', function () { selectType('Examen Final'); });

document.getElementById('archTableBody').addEventListener('click', function (e) {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const action = btn.dataset.action;
  const id     = btn.dataset.id;
  if (action === 'view')   viewArchive(id);
  if (action === 'edit')   editArchive(id);
  if (action === 'delete') confirmDelete(id);
});

document.getElementById('confirmDeleteBtn').addEventListener('click', function () {
  archives = archives.filter(a => a.id !== deleteTargetId);
  persist();
  deleteModal.hide();
  showToast('Archive supprimée.', 'danger');
});

document.querySelector('#archModal .btn-primary').addEventListener('click', saveArchive);

updateStats();
buildAnneeFilter();
renderTable();
