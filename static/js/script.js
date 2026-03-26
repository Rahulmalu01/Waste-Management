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
    function setTheme(theme) {
        const body = document.getElementById("body");

        if (theme === "light") {
            body.classList.remove("bg-slate-900", "text-white");
            body.classList.add("bg-white", "text-black");
            if (themeToggle) themeToggle.textContent = "☀️";
        } else {
            body.classList.remove("bg-white", "text-black");
            body.classList.add("bg-slate-900", "text-white");
            if (themeToggle) themeToggle.textContent = "🌙";
        }
    }
    const savedTheme = localStorage.getItem("theme") || "dark";
    setTheme(savedTheme);
    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const current = localStorage.getItem("theme") === "light" ? "dark" : "light";
            localStorage.setItem("theme", current);
            setTheme(current);
        });
    }
});