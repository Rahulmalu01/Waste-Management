document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("menu-btn");
    const menu = document.getElementById("menu");
    const themeToggle = document.getElementById("theme-toggle");

    if (btn && menu) {
        btn.addEventListener("click", () => {
            menu.classList.toggle("hidden");
            menu.classList.toggle("animate-fadeIn");
        });
    }

    function applyTheme(theme) {
        const html = document.documentElement;

        if (theme === "light") {
            html.classList.remove("dark");
            if (themeToggle) themeToggle.textContent = "☀️";
        } else {
            html.classList.add("dark");
            if (themeToggle) themeToggle.textContent = "🌙";
        }
    }

    const savedTheme = localStorage.getItem("theme") || "dark";
    applyTheme(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const current = document.documentElement.classList.contains("dark") ? "light" : "dark";
            localStorage.setItem("theme", current);
            applyTheme(current);
        });
    }
});
