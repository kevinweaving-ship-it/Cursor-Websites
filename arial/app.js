(function () {
    function line(id) {
        return document.getElementById(id);
    }

    window.setArialLcd = function (top, bottom) {
        if (line("lcd-1")) line("lcd-1").textContent = top == null ? "" : String(top);
        if (line("lcd-2")) line("lcd-2").textContent = bottom == null ? "" : String(bottom);
    };

    document.querySelector(".pad").addEventListener("click", function (ev) {
        var btn = ev.target.closest("[data-key]");
        if (!btn) return;
        var key = btn.getAttribute("data-key");
        if (typeof window.onArialKey === "function") window.onArialKey(key);
    });
})();
