let mode = "login";

const tabs = document.querySelectorAll(".auth-tab");
const form = document.getElementById("authForm");
const message = document.getElementById("authMessage");
const submitBtn = document.getElementById("submitBtn");
const formTitle = document.getElementById("formTitle");
const formSubtitle = document.getElementById("formSubtitle");
const authFooterNote = document.getElementById("authFooterNote");

tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    mode = tab.dataset.mode;

    tabs.forEach(t => t.classList.remove("active"));
    tab.classList.add("active");

    // Alternar visibilidad entre campos de login y registro
    document.querySelectorAll(".login-only").forEach(el => {
      el.style.display = mode === "login" ? "grid" : "none";
    });
    document.querySelectorAll(".register-only").forEach(el => {
      el.style.display = mode === "register" ? "grid" : "none";
    });

    // Ajustar requerimientos de campos según el modo activo
    document.getElementById("name").required = (mode === "register");
    document.getElementById("loginIdentifier").required = (mode === "login");
    document.getElementById("email").required = (mode === "register");
    document.getElementById("studentId").required = (mode === "register");

    if (mode === "login") {
      formTitle.textContent = "Iniciar sesión";
      formSubtitle.textContent = "Accede al sistema completando tus datos.";
      submitBtn.textContent = "Entrar al sistema";
      authFooterNote.style.display = "block";
    } else {
      formTitle.textContent = "Crear cuenta";
      formSubtitle.textContent = "Regístrate para acceder al sistema universitario.";
      submitBtn.textContent = "Crear cuenta";
      authFooterNote.style.display = "none";
    }

    message.textContent = "";
    message.className = "auth-message";

    document.getElementById("password").autocomplete =
      mode === "login" ? "current-password" : "new-password";
  });
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  message.textContent = "";
  message.className = "auth-message";

  const password = document.getElementById("password").value;

  // Inicializar base de usuarios en localStorage si no existe
  let users = JSON.parse(localStorage.getItem("db_users") || "[]");
  const defaultAdmin = { 
    name: "Dr. Carlos Mendoza", 
    email: "admin@universidad.edu.pa", 
    studentId: "ADMIN-01",
    password: "password123", 
    role: "admin" 
  };
  
  if (!users.some(u => u.email === defaultAdmin.email)) {
    users.push(defaultAdmin);
    localStorage.setItem("db_users", JSON.stringify(users));
  }

  if (mode === "register") {
    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const studentId = document.getElementById("studentId").value.trim();
    const confirmPassword = document.getElementById("confirmPassword").value;

    if (!name) return showMessage("Escribe tu nombre completo.", true);
    if (!email && !studentId) return showMessage("Ingresa un correo o número de identificación.", true);
    if (password.length < 8) return showMessage("La contraseña debe tener al menos 8 caracteres.", true);
    if (password !== confirmPassword) return showMessage("Las contraseñas no coinciden.", true);

    if (users.some(u => (email && u.email === email) || (studentId && u.studentId === studentId))) {
      return showMessage("El correo o número de identificación ya se encuentran registrados.", true);
    }

    users.push({ name, email, studentId, password, role: "user" });
    localStorage.setItem("db_users", JSON.stringify(users));

    showMessage("Cuenta creada con éxito. Redirigiendo...", false);
    setTimeout(() => {
      document.querySelector('[data-mode="login"]').click();
      document.getElementById("loginIdentifier").value = email || studentId;
      document.getElementById("password").value = "";
    }, 1000);
  } else {
    const identifier = document.getElementById("loginIdentifier").value.trim();

    // Buscar coincidencia por email, studentId o nombre
    const found = users.find(u => 
      (u.email === identifier || u.studentId === identifier || u.name.toLowerCase() === identifier.toLowerCase()) && 
      u.password === password
    );

    if (!found) {
      return showMessage("Credenciales incorrectas. Verifica tus datos y contraseña.", true);
    }

    localStorage.setItem("currentUser", JSON.stringify({
      name: found.name,
      email: found.email || identifier,
      role: found.role || "user"
    }));

    showMessage("Inicio de sesión exitoso. Entrando...", false);
    
    // Redirección relativa directa al estar dentro de la misma carpeta
    setTimeout(() => {
      window.location.href = "index.html"; 
    }, 800);
  }
});

function showMessage(text, error) {
  message.textContent = text;
  message.className = `auth-message ${error ? "error" : "success"}`;
}