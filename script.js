bien// Obtener el usuario actual desde localStorage o usar valores por defecto
const storedUser = localStorage.getItem("currentUser");
const currentUser = storedUser ? JSON.parse(storedUser) : { role: "admin", name: "Administrador" };
const isStudent = currentUser.role !== "admin";

// Definir menús y títulos según el rol
const navConfig = isStudent ? {
  dashboard: "Portal Estudiantil",
  enrollment: "Matrícula en Línea",
  courses: "Mis Asignaturas y Horarios",
  grades: "Historial Académico",
  profile: "Mi Perfil Académico"
} : {
  dashboard: "Dashboard",
  infrastructure: "Estado de nodos",
  replication: "Red y replicación",
  architecture: "Arquitectura y Diccionario de Datos",
  data: "Distribución de datos",
  fragmentation: "Fragmentación",
  transactions: "Monitor 2PC",
  concurrency: "Control de Concurrencia y Bloqueos",
  queries: "Consultas globales y JOINs",
  recovery: "Logs y fallos",
  users: "Usuarios y permisos"
};

const state = {
  nodes: [
    { name: "Panamá", role: "Información institucional", status: "online", latency: 18, replication: 100 },
    { name: "Coclé", role: "Estudiantes y cursos regionales", status: "online", latency: 16, replication: 98 },
    { name: "Veraguas", role: "Estudiantes y cursos regionales", status: "online", latency: 12, replication: 100 }
  ],
  transactions: [
    { id: "TXN-1041", type: "Actualización", nodes: 3, status: "PREPARE", time: "00:01:12" },
    { id: "TXN-1039", type: "Consulta", nodes: 2, status: "COMMIT", time: "00:03:46" },
    { id: "TXN-1038", type: "Consulta", nodes: 1, status: "EJECUTANDO", time: "00:00:58" }
  ],
  section: "dashboard",
  selectedRoleFilter: "todos"
};

const content = document.getElementById("content");
const pageTitle = document.getElementById("pageTitle");
const toast = document.getElementById("toast");

// Función para obtener únicamente los usuarios registrados en localStorage
function getRegisteredUsers() {
  const storedUsers = localStorage.getItem("registeredUsers") || localStorage.getItem("users");
  if (!storedUsers) {
    return currentUser ? [currentUser] : [];
  }
  try {
    const parsed = JSON.parse(storedUsers);
    return Array.isArray(parsed) ? parsed : [parsed];
  } catch (e) {
    return currentUser ? [currentUser] : [];
  }
}

// Personalizar el menú lateral dinámicamente al cargar la página
function buildSidebarNav() {
  const mainNav = document.getElementById("mainNav");
  if (!mainNav) return;

  if (isStudent) {
    mainNav.innerHTML = `
      <button class="nav-item active" data-section="dashboard">⌂ <span>Inicio / Resumen</span></button>
      <div class="nav-group">
        <div class="nav-title">📚 Matrícula y Oferta</div>
        <button class="nav-item" data-section="enrollment">Inscripción de Asignaturas</button>
        <button class="nav-item" data-section="courses">Horarios y Cursos</button>
      </div>
      <div class="nav-group">
        <div class="nav-title">📊 Mi Rendimiento</div>
        <button class="nav-item" data-section="grades">Calificaciones e Historial</button>
      </div>
      <div class="nav-group">
        <div class="nav-title">👤 Cuenta</div>
        <button class="nav-item" data-section="profile">Datos Personales</button>
      </div>
    `;
  } else {
    mainNav.innerHTML = `
      <button class="nav-item active" data-section="dashboard">⌂ <span>Dashboard</span></button>
      <div class="nav-group">
        <div class="nav-title">▣ Infraestructura</div>
        <button class="nav-item" data-section="infrastructure">Estado de nodos</button>
        <button class="nav-item" data-section="replication">Red y replicación</button>
        <button class="nav-item" data-section="architecture">Arquitectura y Diccionario</button>
      </div>
      <div class="nav-group">
        <div class="nav-title">▤ Datos distribuidos</div>
        <button class="nav-item" data-section="data">Distribución de datos</button>
        <button class="nav-item" data-section="fragmentation">Fragmentación</button>
      </div>
      <div class="nav-group">
        <div class="nav-title">↻ Transacciones</div>
        <button class="nav-item" data-section="transactions">Monitor 2PC</button>
        <button class="nav-item" data-section="concurrency">Concurrencia y Bloqueos</button>
      </div>
      <div class="nav-group">
        <div class="nav-title">⌕ Consultas</div>
        <button class="nav-item" data-section="queries">Consultas globales y JOINs</button>
      </div>
      <div class="nav-group">
        <div class="nav-title">⚠ Recuperación</div>
        <button class="nav-item" data-section="recovery">Logs y fallos</button>
      </div>
      <div class="nav-group">
        <div class="nav-title">⚙ Administración</div>
        <button class="nav-item" data-section="users">Usuarios y permisos</button>
      </div>
    `;
  }

  // Reasignar eventos a los botones del menú
  document.querySelectorAll(".nav-item").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach(x => x.classList.remove("active"));
      btn.classList.add("active");
      state.section = btn.dataset.section;
      if (pageTitle) pageTitle.textContent = navConfig[state.section] || "Portal";
      render();
    });
  });
}

function render() {
  if (!content) return;

  let renderFn;
  if (isStudent) {
    const studentPages = {
      dashboard: studentDashboardPage,
      enrollment: studentEnrollmentPage,
      courses: studentCoursesPage,
      grades: studentGradesPage,
      profile: studentProfilePage
    };
    renderFn = studentPages[state.section] || studentDashboardPage;
  } else {
    const adminPages = {
      dashboard: dashboardPage,
      infrastructure: infrastructurePage,
      replication: replicationPage,
      architecture: arquitecturaDiccionarioPage,
      data: dataPage,
      fragmentation: fragmentationPage,
      transactions: transactionsPage,
      concurrency: concurrencyPage,
      queries: queriesPage,
      recovery: recoveryPage,
      users: usersPage
    };
    renderFn = adminPages[state.section] || dashboardPage;
  }

  content.innerHTML = renderFn();
  bindPageEvents();
}

/* ==========================================
   VISTAS DEL ESTUDIANTE (WEB DE MATRÍCULAS)
   ========================================== */

function studentDashboardPage() {
  return `
    <div class="page-intro">
      <h2>Bienvenido, ${currentUser.name || "Estudiante"}</h2>
      <p>Centro Regional Universitario de Coclé (CRUC) · Facultad de Informática, Electrónica y Comunicación</p>
    </div>

    <section class="kpi-grid">
      <div class="card kpi"><div class="kpi-label">CRÉDITOS MATRICULADOS</div><div class="kpi-value">18</div><div class="kpi-meta">● Semestre activo</div></div>
      <div class="card kpi"><div class="kpi-label">ASIGNATURAS</div><div class="kpi-value">5</div><div class="kpi-meta">● En curso</div></div>
      <div class="card kpi"><div class="kpi-label">ÍNDICE ACADÉMICO</div><div class="kpi-value">2.78</div><div class="kpi-meta">● Excelente</div></div>
      <div class="card kpi"><div class="kpi-label">ESTADO FINANCIERO</div><div class="kpi-value">Paz y Salvo</div><div class="kpi-meta">● Matrícula válida</div></div>
    </section>

    <section class="grid-2">
      <div class="card">
        <div class="card-header"><h2>Avisos de Secretaría Académica</h2><span class="badge blue">Nuevo</span></div>
        <div class="alert success" style="margin-bottom: 12px;">
          <strong>Período de adición y retiro:</strong> Disponible hasta el próximo viernes en la plataforma regional de Coclé.
        </div>
        <p style="font-size: 13px; color: var(--muted); line-height: 1.5;">
          Estimado estudiante, recuerda verificar que tus cupos en los laboratorios de redes y bases de datos estén sincronizados correctamente con el nodo regional.
        </p>
      </div>

      <div class="card">
        <div class="card-header"><h2>Resumen de Sede</h2></div>
        <div class="stat-line"><span>Universidad</span><strong>Universidad Nacional de Panamá</strong></div>
        <div class="stat-line"><span>Centro Regional</span><strong>Coclé (CRUC)</strong></div>
        <div class="stat-line"><span>Carrera</span><strong>Ingeniería Informática</strong></div>
        <div class="stat-line"><span>Conexión con Nodo Central</span><strong style="color:var(--green)">Estable (16 ms)</strong></div>
      </div>
    </section>
  `;
}

function studentEnrollmentPage() {
  return `
    <div class="page-intro">
      <h2>Inscripción de Asignaturas / Matrícula</h2>
      <p>Selecciona las materias habilitadas para tu bloque en el nodo regional de Coclé.</p>
    </div>
    <div class="card" style="margin-bottom: 18px;">
      <div class="card-header"><h2>Oferta Académica Disponibles - Semestre II</h2><span class="badge green">Matrícula Abierta</span></div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Código</th><th>Asignatura</th><th>Créditos</th><th>Profesor</th><th>Cupos Sede Coclé</th><th>Acción</th></tr>
          </thead>
          <tbody>
            <tr><td>IS-411</td><td>Bases de Datos Distribuidas</td><td>4</td><td>Dr. Carlos Mendoza</td><td>12 / 30</td><td><button class="primary-btn enroll-btn" style="padding:6px 12px; margin:0;">Matricular</button></td></tr>
            <tr><td>IS-412</td><td>Procesos y Redes Estocásticas</td><td>3</td><td>Prof. Ana Gómez</td><td>5 / 25</td><td><button class="primary-btn enroll-btn" style="padding:6px 12px; margin:0;">Matricular</button></td></tr>
            <tr><td>IS-413</td><td>Simulación de Sistemas</td><td>3</td><td>Ing. Luis Pérez</td><td>8 / 25</td><td><button class="primary-btn enroll-btn" style="padding:6px 12px; margin:0;">Matricular</button></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function studentCoursesPage() {
  return `
    <div class="page-intro">
      <h2>Mis Asignaturas y Horarios</h2>
      <p>Detalle de tus clases activas en el semestre actual.</p>
    </div>
    <div class="grid-3">
      <div class="card">
        <div class="card-header"><h2>Bases de Datos Distribuidas</h2><span class="badge blue">IS-411</span></div>
        <p style="font-size:12px; color:var(--muted); margin-bottom:10px;">Aula 204 - Edificio de Sistemas</p>
        <div class="stat-line"><span>Días</span><strong>Lunes y Miércoles</strong></div>
        <div class="stat-line"><span>Hora</span><strong>04:00 p.m. - 06:00 p.m.</strong></div>
      </div>
      <div class="card">
        <div class="card-header"><h2>Redes Estocásticas</h2><span class="badge blue">IS-412</span></div>
        <p style="font-size:12px; color:var(--muted); margin-bottom:10px;">Laboratorio de Cómputo 1</p>
        <div class="stat-line"><span>Días</span><strong>Martes y Jueves</strong></div>
        <div class="stat-line"><span>Hora</span><strong>02:00 p.m. - 04:00 p.m.</strong></div>
      </div>
      <div class="card">
        <div class="card-header"><h2>Simulación de Sistemas</h2><span class="badge blue">IS-413</span></div>
        <p style="font-size:12px; color:var(--muted); margin-bottom:10px;">Aula 102</p>
        <div class="stat-line"><span>Días</span><strong>Viernes</strong></div>
        <div class="stat-line"><span>Hora</span><strong>08:00 a.m. - 12:00 p.m.</strong></div>
      </div>
    </div>
  `;
}

function studentGradesPage() {
  return `
    <div class="page-intro">
      <h2>Historial de Calificaciones</h2>
      <p>Consulta de calificaciones parciales y semestrales registradas en el nodo.</p>
    </div>
    <div class="card">
      <div class="card-header"><h2>Calificaciones Recientes</h2><span class="badge blue">Índice Global: 2.78</span></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Código</th><th>Asignatura</th><th>Créditos</th><th>Nota Final</th><th>Estado</th></tr></thead>
          <tbody>
            <tr><td>IS-301</td><td>Ingeniería de Software I</td><td>4</td><td>A</td><td><span class="badge green">Aprobado</span></td></tr>
            <tr><td>IS-302</td><td>Sistemas Operativos II</td><td>4</td><td>B</td><td><span class="badge green">Aprobado</span></td></tr>
            <tr><td>IS-303</td><td>Arquitectura de Computadoras</td><td>3</td><td>A</td><td><span class="badge green">Aprobado</span></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function studentProfilePage() {
  return `
    <div class="page-intro">
      <h2>Perfil Académico del Estudiante</h2>
      <p>Información personal registrada en el sistema universitario de matrículas.</p>
    </div>
    <div class="card" style="max-width: 600px;">
      <div class="card-header"><h2>Datos del Estudiante</h2><span class="badge green">Activo</span></div>
      <div class="stat-line"><span>Nombre Completo</span><strong>${currentUser.name || "N/A"}</strong></div>
      <div class="stat-line"><span>Correo Institucional</span><strong>${currentUser.email || "N/A"}</strong></div>
      <div class="stat-line"><span>Facultad</span><strong>Facultad de Informática, Electrónica y Comunicación</strong></div>
      <div class="stat-line"><span>Sede Regional</span><strong>Centro Regional Universitario de Coclé (CRUC)</strong></div>
      <div class="stat-line"><span>Nivel / Año</span><strong>4° Año (Ingeniería Informática)</strong></div>
    </div>
  `;
}

/* ==========================================
   VISTAS DE ADMINISTRADOR
   ========================================== */

function dashboardPage() {
  return `
    <div class="page-intro">
      <h2>Bienvenido al Sistema de Base de Datos Distribuida</h2>
      <p>Universidad Distribuida 360° · Panamá · Coclé · Veraguas · Modo Administrador</p>
    </div>
    <section class="kpi-grid">
      <div class="card kpi"><div class="kpi-label">NODOS EN LÍNEA</div><div class="kpi-value">3 / 3</div><div class="kpi-meta">● Infraestructura operativa</div></div>
      <div class="card kpi"><div class="kpi-label">REPLICACIÓN</div><div class="kpi-value">Activa</div><div class="kpi-meta">● Sincronización estable</div></div>
      <div class="card kpi"><div class="kpi-label">TRANSACCIONES</div><div class="kpi-value">${state.transactions.length}</div><div class="kpi-meta">● Monitorizadas</div></div>
      <div class="card kpi"><div class="kpi-label">LATENCIA PROMEDIO</div><div class="kpi-value">15.3 ms</div><div class="kpi-meta">● Red estable</div></div>
    </section>
    <section class="grid-2">
      <div class="card">
        <div class="card-header"><h2>Estado de la infraestructura distribuida</h2><span class="badge green">3 nodos activos</span></div>
        ${mapHTML()}
      </div>
      <div>
        <div class="card" style="margin-bottom:18px">
          <div class="card-header"><h2>Latencia entre sedes</h2></div>
          <div class="latency-list">
            <div class="latency-row"><span>Panamá ↔ Coclé</span><strong>18 ms</strong></div>
            <div class="latency-row"><span>Panamá ↔ Veraguas</span><strong>12 ms</strong></div>
            <div class="latency-row"><span>Coclé ↔ Veraguas</span><strong>16 ms</strong></div>
          </div>
        </div>
      </div>
    </section>
  `;
}

function mapHTML() {
  return `
    <div class="map">
      <div class="link l1"></div>
      <div class="link l2"></div>
      <div class="link l3"></div>
      <div class="node panama"><div class="node-icon">🖥️</div><strong>Panamá</strong><small>● En línea</small></div>
      <div class="node cocle"><div class="node-icon">🖥️</div><strong>Coclé</strong><small>● En línea</small></div>
      <div class="node veraguas"><div class="node-icon">🖥️</div><strong>Veraguas</strong><small>● En línea</small></div>
    </div>
  `;
}

function infrastructurePage() {
  return `
    <div class="page-intro"><h2>Infraestructura distribuida</h2><p>Supervisión del estado lógico de los tres servidores universitarios.</p></div>
    <div class="grid-3">
      ${state.nodes.map((n, i) => `
        <div class="card">
          <div class="card-header"><h2>🖥 Nodo ${i+1}</h2><span class="badge ${n.status === "online" ? "green" : "red"}">${n.status === "online" ? "EN LÍNEA" : "FALLA"}</span></div>
          <h3>${n.name}</h3>
          <p style="color:var(--muted);font-size:12px;margin:6px 0 15px">${n.role}</p>
          <div class="stat-line"><span>Latencia</span><strong>${n.latency} ms</strong></div>
          <div class="stat-line"><span>Replicación</span><strong>${n.replication}%</strong></div>
          <div class="progress"><span style="width:${n.replication}%"></span></div>
          <button class="primary-btn node-toggle" data-index="${i}">${n.status === "online" ? "Simular falla" : "Recuperar nodo"}</button>
        </div>
      `).join("")}
    </div>
  `;
}

function replicationPage() {
  return `
    <div class="page-intro"><h2>Red y replicación</h2><p>Visualización de conectividad, latencia y estado de las copias.</p></div>
    <div class="grid-2">
      <div class="card">
        <div class="card-header"><h2>Conectividad entre nodos</h2></div>
        ${["Panamá ↔ Coclé","Panamá ↔ Veraguas","Coclé ↔ Veraguas"].map((x,i) => `
          <div class="latency-row"><span>${x}</span><span><strong>${[18,12,16][i]} ms</strong> <span class="badge green">Conectado</span></span></div>
        `).join("")}
      </div>
      <div class="card">
        <div class="card-header"><h2>Replicación lógica</h2><span class="badge green">ACTIVA</span></div>
        <div class="alert success">✓ Publicaciones y suscripciones operativas.</div>
      </div>
    </div>
  `;
}

function dataPage() {
  return `
    <div class="page-intro"><h2>Distribución de datos</h2><p>Catálogo visual de ubicación, fragmentos y réplicas.</p></div>
    <div class="card"><div class="card-header"><h2>Diccionario de datos distribuido</h2></div><p style="font-size:12px; color:var(--muted);">Tablas de estudiantes y matrículas distribuidas en Coclé y Veraguas.</p></div>
  `;
}

function arquitecturaDiccionarioPage() {
  return `
    <div class="page-intro"><h2>Arquitectura del Sistema</h2><p>Esquema estructural y especificación de metadatos.</p></div>
    <div class="card"><div class="card-header"><h2>Diccionario de Metadatos</h2></div><p style="font-size:12px; color:var(--muted);">Esquemas globales y fragmentados.</p></div>
  `;
}

function fragmentationPage() {
  return `
    <div class="page-intro"><h2>Fragmentación de datos</h2><p>Estrategias horizontal, vertical e híbrida.</p></div>
    <div class="card"><p style="font-size:12px; color:var(--muted);">Fragmentación horizontal por sede regional (Coclé / Veraguas).</p></div>
  `;
}

function transactionsPage() {
  return `
    <div class="page-intro"><h2>Monitor de transacciones distribuidas</h2><p>Seguimiento del ciclo PREPARE → COMMIT / ROLLBACK.</p></div>
    <div class="card">
      <div class="card-header"><h2>Transacciones activas</h2><span class="badge blue">${state.transactions.length} monitorizadas</span></div>
      <div class="table-wrap"><table><thead><tr><th>ID</th><th>Tipo</th><th>Sedes</th><th>Estado</th><th>Tiempo</th></tr></thead>
      <tbody>${state.transactions.map(t => `<tr><td><strong>${t.id}</strong></td><td>${t.type}</td><td>${t.nodes}</td><td><span class="badge ${t.status === "COMMIT" ? "green" : "blue"}">${t.status}</span></td><td>${t.time}</td></tr>`).join("")}</tbody></table></div>
    </div>
  `;
}

function concurrencyPage() {
  return `
    <div class="page-intro"><h2>Control de Concurrencia y Bloqueos</h2><p>Gestión de exclusión mutua y bloqueo de dos fases.</p></div>
    <div class="card"><button class="primary-btn" id="runConcurrency">▶ Ejecutar simulación</button><div id="concurrencyResult" style="margin-top:12px;font-size:12px;color:var(--muted)">Pulsa el botón.</div></div>
  `;
}

function queriesPage() {
  return `
    <div class="page-intro"><h2>Consultas globales</h2><p>Ejecuta una consulta SQL distribuida.</p></div>
    <div class="card"><textarea class="sql-box" id="sqlInput">SELECT * FROM estudiante;</textarea><button class="primary-btn" id="executeQuery">▶ Ejecutar</button><div id="queryResult"></div></div>
  `;
}

function recoveryPage() {
  return `
    <div class="page-intro"><h2>Recuperación ante fallos</h2><p>Logs y checkpoints.</p></div>
    <div class="card"><div class="card-header"><h2>WAL / LOG</h2></div><div class="alert success">✓ Sistema operativo estable</div></div>
  `;
}

/* ==========================================
   VISTA DE USUARIOS Y PERMISOS (DATOS REALES)
   ========================================== */

function usersPage() {
  return `
    <div class="page-intro">
      <h2>Usuarios y Permisos</h2>
      <p>Administración de cuentas registradas en el sistema.</p>
    </div>

    <div class="card">
      <div class="card-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
        <h2>Usuarios Registrados</h2>
        <div>
          <label for="roleFilter" style="font-size:13px; font-weight:600; margin-right:8px;">Filtrar por rol:</label>
          <select id="roleFilter" style="padding:6px 12px; border-radius:6px; border:1px solid #ccc; background-color:#fff;">
            <option value="todos" ${state.selectedRoleFilter === 'todos' ? 'selected' : ''}>Todos los roles</option>
            <option value="admin" ${state.selectedRoleFilter === 'admin' ? 'selected' : ''}>Administrador</option>
            <option value="docente" ${state.selectedRoleFilter === 'docente' ? 'selected' : ''}>Docente</option>
            <option value="estudiante" ${state.selectedRoleFilter === 'estudiante' ? 'selected' : ''}>Estudiante</option>
          </select>
        </div>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>USUARIO</th>
              <th>ROL</th>
              <th>NODO / SEDE</th>
              <th>ÚLTIMO INICIO DE SESIÓN</th>
              <th>ESTADO</th>
            </tr>
          </thead>
          <tbody id="usersTableBody">
            ${generateUserTableRows(state.selectedRoleFilter)}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// Genera las filas exclusivamente leyendo los datos reales de localStorage
function generateUserTableRows(filterRole) {
  const users = getRegisteredUsers();

  const filteredUsers = filterRole === "todos" 
    ? users 
    : users.filter(user => {
        const userRole = (user.role || user.rol || "").toLowerCase();
        return userRole === filterRole.toLowerCase();
      });

  if (filteredUsers.length === 0) {
    return `<tr><td colspan="5" style="text-align:center; color:var(--muted); padding:15px;">No hay usuarios registrados con el rol seleccionado.</td></tr>`;
  }

  return filteredUsers.map(u => {
    const roleName = u.role || u.rol || "Sin rol";
    const displayName = u.name || u.usuario || u.nombre || "Usuario";
    const email = u.email || "Sin correo registrado";
    const node = u.node || u.nodo || u.sede || "Panamá";
    const lastLogin = u.lastLogin || u.ultimoInicio || "Reciente";
    const status = u.status || u.estado || "En línea";

    return `
      <tr>
        <td>
          <strong>${displayName}</strong><br>
          <small style="color:var(--muted,#777);">${email}</small>
        </td>
        <td><span class="badge blue">${roleName}</span></td>
        <td>${node}</td>
        <td>${lastLogin}</td>
        <td><span class="badge ${status === "En línea" || status === "online" ? "green" : "red"}">${status}</span></td>
      </tr>
    `;
  }).join("");
}

/* ==========================================
   EVENTOS DINÁMICOS
   ========================================== */

function bindPageEvents() {
  // Evento para matriculación del estudiante
  document.querySelectorAll(".enroll-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      btn.disabled = true;
      btn.textContent = "Matriculado";
      btn.style.backgroundColor = "var(--green, #2e7d32)";
      showToast("¡Asignatura matriculada con éxito en el nodo de Coclé!");
    });
  });

  // Evento del filtro por rol en Usuarios y Permisos
  const roleFilterEl = document.getElementById("roleFilter");
  if (roleFilterEl) {
    roleFilterEl.addEventListener("change", (e) => {
      state.selectedRoleFilter = e.target.value;
      const tbody = document.getElementById("usersTableBody");
      if (tbody) {
        tbody.innerHTML = generateUserTableRows(state.selectedRoleFilter);
      }
    });
  }

  const runConcurrency = document.getElementById("runConcurrency");
  if (runConcurrency) {
    runConcurrency.addEventListener("click", () => {
      const resultEl = document.getElementById("concurrencyResult");
      if (resultEl) resultEl.innerHTML = `<div class="alert success">✓ Transacción completada con éxito.</div>`;
      showToast("Simulación finalizada");
    });
  }

  const executeQuery = document.getElementById("executeQuery");
  if (executeQuery) {
    executeQuery.addEventListener("click", () => {
      const queryResultEl = document.getElementById("queryResult");
      if (queryResultEl) queryResultEl.innerHTML = `<div class="alert success" style="margin-top:10px;">✓ Consulta ejecutada correctamente a través de los nodos.</div>`;
      showToast("Consulta SQL ejecutada");
    });
  }

  document.querySelectorAll(".node-toggle").forEach(btn => {
    btn.addEventListener("click", () => {
      const index = parseInt(btn.dataset.index, 10);
      if (!isNaN(index) && state.nodes[index]) {
        state.nodes[index].status = state.nodes[index].status === "online" ? "offline" : "online";
        render();
        showToast(`Nodo ${state.nodes[index].name} actualizado`);
      }
    });
  });
}

function showToast(message) {
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 2200);
}

function updateClock() {
  const clockEl = document.getElementById("clock");
  if (clockEl) {
    const now = new Date();
    clockEl.textContent = now.toLocaleString("es-PA", {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
    });
  }
}

// Inicialización de componentes al cargar el archivo
setInterval(updateClock, 1000);
updateClock();
buildSidebarNav();
render();