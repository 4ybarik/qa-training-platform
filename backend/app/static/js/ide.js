/* Встроенная IDE: файлы student_tests, редактор, запуск тестов, поиск локаторов.
 * Работает на fetch + CodeMirror (CDN); без CDN деградирует до обычной textarea. */
(function () {
  "use strict";

  var currentFile = null;
  var editor = null;          // CodeMirror instance
  var textarea = document.getElementById("ide-editor");

  function value() { return editor ? editor.getValue() : textarea.value; }
  function setValue(text) {
    if (editor) { editor.setValue(text); }
    else { textarea.value = text; }
  }
  function toast(message, isError) {
    var el = document.getElementById("ide-toast");
    el.textContent = message;
    el.hidden = false;
    clearTimeout(el._timer);
    el._timer = setTimeout(function () { el.hidden = true; }, 3500);
  }

  if (window.CodeMirror) {
    editor = window.CodeMirror.fromTextArea(textarea, {
      mode: "python", lineNumbers: true, indentUnit: 4, tabSize: 4,
      indentWithTabs: false, lineWrapping: true,
    });
    editor.setOption("extraKeys", {
      "Ctrl-S": function () { saveFile(); return false; },
      "Cmd-S": function () { saveFile(); return false; },
    });
  } else {
    textarea.addEventListener("keydown", function (event) {
      if ((event.ctrlKey || event.metaKey) && event.key === "s") {
        event.preventDefault();
        saveFile();
      }
    });
  }

  function setButtons(enabled) {
    document.getElementById("ide-save-btn").disabled = !enabled;
    document.getElementById("ide-run-btn").disabled = !enabled;
  }

  function showOutput(text, ok) {
    var out = document.getElementById("ide-output");
    out.hidden = false;
    out.textContent = text || "(пустой вывод)";
    out.classList.toggle("ide-ok", Boolean(ok));
    out.classList.toggle("ide-fail", ok === false);
  }

  /* ---------- Файлы ---------- */
  function loadFiles() {
    fetch("/api/ide/files")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById("ide-file-list");
        list.textContent = "";
        data.files.forEach(function (path) {
          var button = document.createElement("button");
          button.type = "button";
          button.className = "ide-file-item";
          button.dataset.path = path;
          button.setAttribute("data-testid", "ide-file-" + path);
          button.textContent = path;
          button.addEventListener("click", function () { openFile(path); });
          list.appendChild(button);
        });
      })
      .catch(function () { toast("Не удалось загрузить список файлов", true); });
  }

  function markActive(path) {
    document.querySelectorAll(".ide-file-item").forEach(function (el) {
      el.classList.toggle("active", el.dataset.path === path);
    });
  }

  function openFile(path) {
    fetch("/api/ide/file?path=" + encodeURIComponent(path))
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        currentFile = path;
        setValue(data.content);
        document.getElementById("ide-current-file").textContent = path;
        document.getElementById("ide-output").hidden = true;
        setButtons(true);
        markActive(path);
      })
      .catch(function () { toast("Файл недоступен: " + path, true); });
  }

  function saveFile() {
    if (!currentFile) { toast("Сначала выберите файл", true); return; }
    fetch("/api/ide/file", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: currentFile, content: value() }),
    })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function () { toast("Сохранено: " + currentFile); })
      .catch(function () { toast("Ошибка сохранения", true); });
  }

  function runTests() {
    if (!currentFile) { toast("Сначала выберите файл", true); return; }
    saveFile();
    showOutput("Запуск…");
    fetch("/api/ide/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: currentFile }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) { showOutput(data.output, data.exit_code === 0); })
      .catch(function () { showOutput("Ошибка запуска", false); });
  }

  /* ---------- Локаторы ---------- */
  function searchLocators(event) {
    event.preventDefault();
    var url = document.getElementById("ide-locator-url").value.trim();
    var status = document.getElementById("ide-locator-status");
    var results = document.getElementById("ide-locator-results");
    var preview = document.getElementById("ide-preview");
    status.textContent = "Загрузка…";
    results.textContent = "";
    preview.src = url;

    fetch("/api/ide/locators?url=" + encodeURIComponent(url))
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        status.textContent = "Найдено локаторов: " + data.count + " (" + data.final_url + ")";
        data.locators.forEach(function (item) {
          var li = document.createElement("li");
          li.className = "ide-locator-item";
          li.setAttribute("data-testid", "ide-locator-" + item.testid);

          var copy = document.createElement("button");
          copy.type = "button";
          copy.className = "btn ide-copy-btn";
          copy.textContent = "копировать";
          copy.addEventListener("click", function () {
            navigator.clipboard.writeText(item.selector).then(
              function () { toast("Скопировано: " + item.selector); },
              function () { toast("Буфер обмена недоступен", true); },
            );
          });

          var code = document.createElement("code");
          code.textContent = item.testid;
          var hint = document.createElement("div");
          hint.className = "ide-locator-text";
          hint.textContent = "<" + item.tag + "> " + item.text;

          li.appendChild(copy);
          li.appendChild(code);
          li.appendChild(hint);
          results.appendChild(li);
        });
        if (!data.locators.length) { status.textContent = "data-testid не найдены."; }
      })
      .catch(function () { status.textContent = "Ошибка запроса страницы"; });
  }

  document.getElementById("ide-save-btn").addEventListener("click", saveFile);
  document.getElementById("ide-run-btn").addEventListener("click", runTests);
  document.getElementById("ide-locator-form").addEventListener("submit", searchLocators);

  loadFiles();
})();
