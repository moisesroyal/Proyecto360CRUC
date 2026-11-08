(function () {
  try {
    // Obtener sesión guardada en localStorage por auth.js
    const storedUser = localStorage.getItem("currentUser");

    if (!storedUser) {
      window.location.replace("auth.html");
      return;
    }

    const user = JSON.parse(storedUser);
    window.currentUser = user;

    // Actualizar elementos de interfaz en el topbar
    const name = document.getElementById("userName");
    const role = document.getElementById("userRole");
    const avatar = document.getElementById("userAvatar");

    if (name) name.textContent = user.name || "Usuario";
    if (role) role.textContent = user.role === "admin" ? "Administrador" : "Usuario académico";
    if (avatar) avatar.textContent = (user.name || "U").trim().charAt(0).toUpperCase();

    document.body.dataset.role = user.role;

    // Mostrar/ocultar elementos exclusivos de administrador
    document.querySelectorAll(".admin-only").forEach(el => {
      el.hidden = user.role !== "admin";
    });

    // Configurar botón de cerrar sesión
    const logout = document.getElementById("logoutBtn");
    if (logout) {
      logout.addEventListener("click", () => {
        logout.disabled = true;
        localStorage.removeItem("currentUser");
        window.location.replace("auth.html");
      });
    }
  } catch (error) {
    console.error("Error en la verificación de autenticación:", error);
    localStorage.removeItem("currentUser");
    window.location.replace("auth.html");
  }
})();