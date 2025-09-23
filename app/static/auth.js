const el = id => document.getElementById(id);

document.addEventListener("DOMContentLoaded", () => {
  // ---- LOGIN ----
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async e => {
      e.preventDefault();
      const res = await fetch("/login", {
        method: "POST",
        body: new FormData(loginForm),
      });
      if (!res.ok) return alert("Login failed");
      const j = await res.json();
      localStorage.setItem("token", j.access_token);
      window.location.href = "/static/chat.html";
    });
  }

  // ---- SIGNUP ----
  const signupForm = document.getElementById("signupForm");
  if (signupForm) {
    signupForm.addEventListener("submit", async e => {
      e.preventDefault();
      const res = await fetch("/signup", {
        method: "POST",
        body: new FormData(signupForm),
      });
      if (!res.ok) return alert("Signup failed");
      alert("✅ Signup successful! Please log in.");
      window.location.href = "/static/login.html";
    });
  }
});
