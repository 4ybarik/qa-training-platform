/* QA Training Platform — клиентская логика.
   Намеренно без сборщиков и фреймворков: предсказуемый DOM для UI-автотестов. */
window.QATP = (function () {
  "use strict";

  function toast(message) {
    const root = document.getElementById("toast-root");
    if (!root) return;
    const el = document.createElement("div");
    el.className = "toast";
    el.setAttribute("data-testid", "toast");
    el.textContent = message;
    root.appendChild(el);
    setTimeout(() => el.remove(), 3000);
  }

  // ---------- Модальные окна ----------
  function openModal(id) {
    const m = document.getElementById(id);
    if (m) m.hidden = false;
  }
  function closeModal(id) {
    const m = document.getElementById(id);
    if (m) m.hidden = true;
  }

  // ---------- Переключение представления (таблица / карточки) ----------
  function setView(mode) {
    const table = document.getElementById("courses-table");
    const cards = document.getElementById("courses-cards");
    if (!table || !cards) return;
    const showCards = mode === "cards";
    table.hidden = showCards;
    cards.hidden = !showCards;
  }

  // ---------- Вкладки ----------
  function selectTab(btn, panelId) {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => (p.hidden = true));
    btn.classList.add("active");
    const panel = document.getElementById(panelId);
    if (panel) panel.hidden = false;
  }

  // ---------- WebSocket: лента уведомлений ----------
  function connectNotifications() {
    const feed = document.getElementById("ws-feed");
    if (!feed || !("WebSocket" in window)) return;
    const proto = location.protocol === "https:" ? "wss" : "ws";
    try {
      const ws = new WebSocket(`${proto}://${location.host}/ws/notifications`);
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const li = document.createElement("li");
        li.setAttribute("data-testid", "ws-event");
        li.textContent = data.message;
        feed.prepend(li);
      };
    } catch (e) {
      /* ignore */
    }
  }

  // ---------- Экзамен: таймер, прогресс, drag-and-drop ----------
  function initExam() {
    const timer = document.querySelector('[data-testid="countdown-timer"]');
    if (timer) {
      let seconds = parseInt(timer.dataset.minutes || "15", 10) * 60;
      const tick = () => {
        const m = String(Math.floor(seconds / 60)).padStart(2, "0");
        const s = String(seconds % 60).padStart(2, "0");
        timer.textContent = `${m}:${s}`;
        if (seconds > 0) seconds--;
      };
      tick();
      setInterval(tick, 1000);
    }

    // Прогресс по числу отвеченных вопросов
    const form = document.querySelector('[data-testid="exam-form"]');
    const fill = document.getElementById("exam-progress-fill");
    if (form && fill) {
      const questions = form.querySelectorAll(".question");
      const update = () => {
        let answered = 0;
        questions.forEach((q) => {
          if (q.querySelector("input:checked, textarea:not(:placeholder-shown)")) answered++;
        });
        fill.style.width = questions.length ? (answered / questions.length) * 100 + "%" : "0%";
      };
      form.addEventListener("change", update);
      form.addEventListener("input", update);
    }

    // Drag and drop
    document.querySelectorAll(".dnd").forEach((dnd) => {
      const target = dnd.querySelector(".dnd-target");
      const qid = target ? target.dataset.question : null;
      dnd.querySelectorAll(".dnd-item").forEach((item) => {
        item.addEventListener("dragstart", (e) => {
          e.dataTransfer.setData("text/plain", item.dataset.id);
        });
      });
      if (target) {
        target.addEventListener("dragover", (e) => {
          e.preventDefault();
          target.classList.add("over");
        });
        target.addEventListener("dragleave", () => target.classList.remove("over"));
        target.addEventListener("drop", (e) => {
          e.preventDefault();
          target.classList.remove("over");
          const id = e.dataTransfer.getData("text/plain");
          // Ищем элемент только в источнике, чтобы повторный drop уже
          // перемещённого элемента не создавал дублей.
          const source = dnd.querySelector(".dnd-source");
          const dropped = source ? source.querySelector(`.dnd-item[data-id="${id}"]`) : null;
          if (dropped) {
            target.appendChild(dropped);
            // Убираем старый hidden для этого id, если он уже был добавлен
            // (повторный drop уже перемещённого элемента не должен дублировать поле).
            const existing = target.querySelector(`input[type="hidden"][value="${id}"]`);
            if (existing) existing.remove();
            // Сервер сверяет набор id без учёта порядка — см. ExamService._is_correct.
            const hidden = document.createElement("input");
            hidden.type = "hidden";
            hidden.name = `q_${qid}`;
            hidden.value = id;
            hidden.setAttribute("data-testid", `dnd-selected-${id}`);
            target.appendChild(hidden);
          }
        });
      }
    });
  }

  // ---------- Уведомления ----------
  function filterNotifications(status) {
    document.querySelectorAll('[data-testid^="notification-"]').forEach((li) => {
      if (!li.dataset.status) return;
      li.style.display = status === "ALL" || li.dataset.status === status ? "" : "none";
    });
  }

  async function markRead(id, btn) {
    try {
      const r = await fetch(`/api/notifications/${id}/read`, { method: "POST" });
      if (r.ok) {
        const li = btn.closest(".notif-item");
        if (li) li.dataset.status = "READ";
        const badge = document.querySelector(`[data-testid="notification-status-${id}"]`);
        if (badge) badge.textContent = "READ";
        toast("Отмечено как прочитанное");
      }
    } catch (e) {
      toast("Ошибка сети");
    }
  }

  async function deleteNotification(id, btn) {
    try {
      const r = await fetch(`/api/notifications/${id}`, { method: "DELETE" });
      if (r.ok) {
        const li = btn.closest(".notif-item");
        if (li) li.remove();
        toast("Удалено");
      }
    } catch (e) {
      toast("Ошибка сети");
    }
  }

  // ---------- Бесконечная прокрутка ----------
  function initInfiniteScroll() {
    const sentinel = document.getElementById("infinite-sentinel");
    const list = document.getElementById("notif-list");
    if (!sentinel || !list || !("IntersectionObserver" in window)) return;
    let batch = 0;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && batch < 3) {
          batch++;
          for (let i = 0; i < 5; i++) {
            const li = document.createElement("li");
            li.className = "notif-item";
            li.dataset.status = "READ";
            li.setAttribute("data-testid", `notification-extra-${batch}-${i}`);
            li.textContent = `Подгруженное уведомление (партия ${batch})`;
            list.appendChild(li);
          }
        }
      });
    });
    observer.observe(sentinel);
  }

  // ---------- Админ: смена роли ----------
  async function changeRole(userId, role) {
    try {
      const r = await fetch(`/api/admin/users/${userId}/role`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      if (r.ok) {
        const cell = document.querySelector(`[data-testid="user-role-${userId}"]`);
        if (cell) cell.textContent = role;
        toast("Роль обновлена");
      } else {
        toast("Не удалось обновить роль");
      }
    } catch (e) {
      toast("Ошибка сети");
    }
  }

  // ---------- Playground ----------
  async function initPlayground() {
    try {
      const r = await fetch("/api/playground");
      if (!r.ok) return;
      const cfg = await r.json();
      document.getElementById("pg-enabled").checked = cfg.enabled;
      document.getElementById("pg-latency").value = cfg.latency_ms;
      document.getElementById("pg-error").value = cfg.error_rate;
    } catch (e) {
      /* ignore */
    }
  }

  async function applyPlayground() {
    const body = {
      enabled: document.getElementById("pg-enabled").checked,
      latency_ms: parseInt(document.getElementById("pg-latency").value, 10),
      error_rate: parseFloat(document.getElementById("pg-error").value),
    };
    try {
      const r = await fetch("/api/playground", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const status = document.getElementById("pg-status");
      if (r.ok && status) status.textContent = "Применено";
      toast("Настройки Playground применены");
    } catch (e) {
      toast("Ошибка сети");
    }
  }

  function spawnDynamic() {
    const area = document.getElementById("dynamic-area");
    if (!area) return;
    area.textContent = "Загрузка…";
    setTimeout(() => {
      area.innerHTML =
        '<div class="badge badge-ok" data-testid="dynamic-element">Элемент появился</div>';
    }, 2000);
  }

  return {
    toast, openModal, closeModal, setView, selectTab, connectNotifications,
    initExam, filterNotifications, markRead, deleteNotification,
    initInfiniteScroll, changeRole, initPlayground, applyPlayground, spawnDynamic,
  };
})();
