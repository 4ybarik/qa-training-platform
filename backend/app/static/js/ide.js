/* Встроенная IDE: файлы student_tests, редактор, запуск тестов, поиск локаторов.
 * Работает на fetch + CodeMirror (CDN); без CDN деградирует до обычной textarea. */
(function () {
  "use strict";

  var currentFile = null;
  var query = new URLSearchParams(window.location.search);
  var requestedFile = query.get("file");
  var currentChallenge = query.get("challenge");
  var editor = null;          // CodeMirror instance
  var textarea = document.getElementById("ide-editor");
  var MESSAGES = window.QATP_MESSAGES || {};

  function msg(key, values) {
    var template = MESSAGES[key] || key;
    return template.replace(/\{(\w+)\}/g, function (_, name) {
      return values && values[name] !== undefined ? String(values[name]) : "";
    });
  }

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
    out.textContent = text || msg("ide_empty_output");
    out.classList.toggle("ide-ok", Boolean(ok));
    out.classList.toggle("ide-fail", ok === false);
  }

  /* ---------- Файлы ---------- */
  function loadFiles() {
    return fetch("/api/ide/files")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById("ide-file-list");
        list.textContent = "";
        data.files.forEach(function (path) {
          var row = document.createElement("div");
          row.className = "ide-file-row";

          var button = document.createElement("button");
          button.type = "button";
          button.className = "ide-file-item";
          button.dataset.path = path;
          button.setAttribute("data-testid", "ide-file-" + path);
          button.textContent = path;
          button.title = path;
          button.addEventListener("click", function () { openFile(path); });

          var del = document.createElement("button");
          del.type = "button";
          del.className = "ide-file-del";
          del.textContent = "✕";
          del.title = msg("ide_delete_title");
          del.setAttribute("data-testid", "ide-delete-" + path);
          del.addEventListener("click", function () { deleteFile(path); });

          row.appendChild(button);
          row.appendChild(del);
          list.appendChild(row);
        });
      })
      .catch(function () { toast(msg("ide_files_error"), true); });
  }

  function deleteFile(path) {
    if (!window.confirm(msg("ide_delete_confirm", { path: path }))) {
      return;
    }
    fetch("/api/ide/file?path=" + encodeURIComponent(path), { method: "DELETE" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function () {
        toast(msg("ide_deleted", { path: path }));
        if (currentFile === path) {
          currentFile = null;
          setValue("");
          document.getElementById("ide-current-file").textContent = msg("ide_no_file");
          document.getElementById("ide-output").hidden = true;
          setButtons(false);
        }
        loadFiles();
      })
      .catch(function () { toast(msg("ide_delete_error", { path: path }), true); });
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
      .catch(function () { toast(msg("ide_open_error", { path: path }), true); });
  }

  function saveFile() {
    if (!currentFile) { toast(msg("ide_pick_file"), true); return Promise.reject(new Error("no file")); }
    return fetch("/api/ide/file", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: currentFile, content: value() }),
    })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function () { toast(msg("ide_saved", { path: currentFile })); })
      .catch(function () { toast(msg("ide_save_error"), true); });
  }

  /* ---------- Создание нового файла ---------- */
  var NEW_FILE_RE = /^(?:(api|contract|integration|ui)\/)?(test_[A-Za-z0-9_.-]+\.py)$/;

  function createFile() {
    var raw = document.getElementById("ide-new-file").value.trim();
    if (!raw) { toast(msg("ide_create_name_hint"), true); return; }
    var match = NEW_FILE_RE.exec(raw);
    if (!match) {
      toast(msg("ide_create_bad_name"), true);
      return;
    }
    var path = (match[1] || "api") + "/" + match[2];
    var skeleton = [
      '"""' + msg("ide_skeleton_docstring") + '"""',
      "import pytest",
      "",
      "",
      "@pytest.mark.api",
      "def test_" + match[2].replace(/^test_/, "").replace(/\.py$/, "") +
        "(api_client, run_headers):",
      '    response = api_client.get("/health")',
      "",
      "    assert response.status_code == 200",
      "",
    ].join("\n");
    fetch("/api/ide/files", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: path, content: value() ? value() : skeleton }),
    })
      .then(function (r) {
        if (!r.ok) { return r.json().then(function (e) { throw new Error(e.detail || r.status); }); }
        return r.json();
      })
      .then(function () {
        document.getElementById("ide-new-file").value = "";
        loadFiles();
        openFile(path);
        toast(msg("ide_created", { path: path }));
      })
      .catch(function (err) { toast(msg("ide_create_error", { message: err.message }), true); });
  }

  function runTests() {
    if (!currentFile) { toast(msg("ide_pick_file"), true); return; }
    showOutput(msg("ide_running"));
    saveFile()
      .then(function () {
        var payload = { path: currentFile };
        if (currentChallenge && currentFile === requestedFile) {
          payload.challenge_slug = currentChallenge;
        }
        return fetch("/api/ide/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      })
      .then(function (r) {
        return r.json().then(function (data) {
          if (!r.ok) { throw new Error(data.detail || r.status); }
          return data;
        });
      })
      .then(function (data) {
        var lines = [];
        if (data.score !== undefined) {
          lines.push("RESULT: " + data.score + "% · " + (data.passed ? "PASSED" : "NOT PASSED"));
          lines.push("TESTS: " + (data.tests_passed || 0) + "/" + (data.tests_collected || 0) +
            " · " + (data.duration_ms || 0) + " ms");
        }
        (data.criteria || []).forEach(function (item) {
          lines.push((item.passed ? "✓ " : "✗ ") + item.title +
            (item.details ? " — " + item.details : ""));
        });
        if (lines.length) { lines.push("", "PYTEST OUTPUT:"); }
        lines.push(data.output || msg("ide_empty_output"));
        showOutput(lines.join("\n"), Boolean(data.passed));
      })
      .catch(function () { showOutput(msg("ide_run_error"), false); });
  }

  /* ---------- Локаторы ---------- */
  function searchLocators(event) {
    event.preventDefault();
    var url = document.getElementById("ide-locator-url").value.trim();
    var status = document.getElementById("ide-locator-status");
    var results = document.getElementById("ide-locator-results");
    var preview = document.getElementById("ide-preview");
    status.textContent = msg("ide_locators_loading");
    results.textContent = "";
    preview.src = url;

    fetch("/api/ide/locators?url=" + encodeURIComponent(url))
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        status.textContent = msg("ide_locators_found", { count: data.count, path: data.final_url });
        data.locators.forEach(function (item) {
          var li = document.createElement("li");
          li.className = "ide-locator-item";
          li.setAttribute("data-testid", "ide-locator-" + item.testid);

          var copy = document.createElement("button");
          copy.type = "button";
          copy.className = "btn ide-copy-btn";
          copy.textContent = msg("ide_copy_btn");
          copy.addEventListener("click", function () {
            navigator.clipboard.writeText(item.selector).then(
              function () { toast(msg("ide_copied", { selector: item.selector })); },
              function () { toast(msg("ide_clipboard_error"), true); },
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
        if (!data.locators.length) { status.textContent = msg("ide_locators_none"); }
      })
      .catch(function () { status.textContent = msg("ide_locators_error"); });
  }

  document.getElementById("ide-save-btn").addEventListener("click", saveFile);
  document.getElementById("ide-run-btn").addEventListener("click", runTests);
  document.getElementById("ide-create-btn").addEventListener("click", createFile);
  document.getElementById("ide-new-file").addEventListener("keydown", function (event) {
    if (event.key === "Enter") { event.preventDefault(); createFile(); }
  });
  document.getElementById("ide-locator-form").addEventListener("submit", searchLocators);

  if (currentChallenge) {
    var context = document.getElementById("ide-lesson-context");
    context.hidden = false;
    document.getElementById("ide-lesson-label").textContent = currentChallenge;
    document.getElementById("ide-lesson-link").href = "/learning/" + encodeURIComponent(currentChallenge);
  }
  loadFiles().then(function () {
    if (requestedFile) { openFile(requestedFile); }
  });
})();
