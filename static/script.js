(function () {
  const modeTabs = document.getElementById("input-mode-tabs");
  const pastePanel = document.getElementById("paste-panel");
  const docPanel = document.getElementById("doc-panel");
  const assignmentText = document.getElementById("assignment-text");
  const assignmentFile = document.getElementById("assignment-file");
  const browseBtn = document.getElementById("browse-btn");
  const fileDrop = document.getElementById("file-drop");
  const fileSelected = document.getElementById("file-selected");
  const extractedPreviewWrap = document.getElementById("extracted-preview-wrap");
  const extractedPreview = document.getElementById("extracted-preview");
  const domainInput = document.getElementById("domain");
  const questionTitleInput = document.getElementById("question-title");
  const filesToImplement = document.getElementById("files-to-implement");
  const filesScaffold = document.getElementById("files-scaffold");
  const analyzeBtn = document.getElementById("analyze-btn");
  const analyzeSpinner = document.getElementById("analyze-spinner");
  const generateBtn = document.getElementById("generate-btn");
  const generateSpinner = document.getElementById("generate-spinner");
  const errorBanner = document.getElementById("error-banner");
  const analysisSection = document.getElementById("analysis-section");
  const analysisSummary = document.getElementById("analysis-summary");
  const coverageGrid = document.getElementById("coverage-grid");
  const outOfSyllabus = document.getElementById("out-of-syllabus");
  const outList = document.getElementById("out-list");
  const resultSection = document.getElementById("result-section");
  const resultTitle = document.getElementById("result-title");
  const resultMeta = document.getElementById("result-meta");
  const downloadBtn = document.getElementById("download-btn");
  const folderTabs = document.getElementById("folder-tabs");
  const fileList = document.getElementById("file-list");
  const filePreviewHeader = document.getElementById("file-preview-header");
  const fileContent = document.getElementById("file-content");
  const structureRationale = document.getElementById("structure-rationale");
  const studentFilesList = document.getElementById("student-files-list");
  const scaffoldFilesList = document.getElementById("scaffold-files-list");
  const syllabusTopicsList = document.getElementById("syllabus-topics-list");
  const apiKeyInput = document.getElementById("api-key");
  const saveApiKeyBtn = document.getElementById("save-api-key-btn");
  const apiKeyStatus = document.getElementById("api-key-status");

  let inputMode = "paste";
  let selectedFile = null;
  let analysisData = null;
  let assignmentTextCache = "";
  let currentPreview = null;
  let activeFolder = "prefilled";
  let activeFile = null;

  function setAnalyzeLoading(loading) {
    analyzeBtn.disabled = loading;
    analyzeSpinner.classList.toggle("hidden", !loading);
  }

  function setGenerateLoading(loading) {
    generateBtn.disabled = loading || !getSelectedConcepts().length;
    generateSpinner.classList.toggle("hidden", !loading);
  }

  function showError(message) {
    errorBanner.textContent = message;
    errorBanner.classList.remove("hidden");
  }

  function hideError() {
    errorBanner.classList.add("hidden");
    errorBanner.textContent = "";
  }

  saveApiKeyBtn.addEventListener("click", async () => {
    const apiKey = apiKeyInput.value.trim();
    apiKeyStatus.textContent = "";
    saveApiKeyBtn.disabled = true;

    try {
      const res = await fetch("/settings/api-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey }),
      });
      const data = await res.json();
      apiKeyStatus.textContent = data.message || data.error || "Could not save API key.";
      apiKeyStatus.classList.toggle("error", !res.ok);
      if (res.ok) apiKeyInput.value = "";
    } catch (err) {
      apiKeyStatus.textContent = "Network error — is the server running?";
      apiKeyStatus.classList.add("error");
    } finally {
      saveApiKeyBtn.disabled = false;
    }
  });

  function switchMode(mode) {
    inputMode = mode;
    modeTabs.querySelectorAll(".mode-tab").forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.mode === mode);
    });
    pastePanel.classList.toggle("hidden", mode !== "paste");
    docPanel.classList.toggle("hidden", mode !== "doc");
    hideError();
  }

  modeTabs.addEventListener("click", (e) => {
    const tab = e.target.closest(".mode-tab");
    if (tab) switchMode(tab.dataset.mode);
  });

  browseBtn.addEventListener("click", () => assignmentFile.click());

  assignmentFile.addEventListener("change", () => {
    selectedFile = assignmentFile.files[0] || null;
    if (selectedFile) {
      fileSelected.textContent = selectedFile.name;
      fileSelected.classList.remove("hidden");
      extractedPreviewWrap.classList.add("hidden");
      extractedPreview.textContent = "";
    } else {
      fileSelected.classList.add("hidden");
    }
  });

  fileDrop.addEventListener("dragover", (e) => {
    e.preventDefault();
    fileDrop.classList.add("drag-over");
  });

  fileDrop.addEventListener("dragleave", () => {
    fileDrop.classList.remove("drag-over");
  });

  fileDrop.addEventListener("drop", (e) => {
    e.preventDefault();
    fileDrop.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) {
      selectedFile = file;
      const dt = new DataTransfer();
      dt.items.add(file);
      assignmentFile.files = dt.files;
      fileSelected.textContent = file.name;
      fileSelected.classList.remove("hidden");
    }
  });

  async function getAssignmentPayload() {
    if (inputMode === "paste") {
      const text = assignmentText.value.trim();
      if (!text) throw new Error("Paste the assignment text first.");
      return { type: "json", body: { text } };
    }

    if (selectedFile) {
      const formData = new FormData();
      formData.append("file", selectedFile);
      return { type: "form", body: formData };
    }

    const text = assignmentText.value.trim();
    if (text) {
      const formData = new FormData();
      formData.append("text", text);
      return { type: "form", body: formData };
    }

    throw new Error("Upload a document or paste text in the other tab.");
  }

  function updateGenerateButton() {
    generateBtn.disabled = !analysisData || !getSelectedConcepts().length;
  }

  function getSelectedConcepts() {
    const selected = [];
    coverageGrid.querySelectorAll(".concept-check:checked").forEach((cb) => {
      selected.push({
        topic_id: cb.dataset.topicId,
        concept: cb.dataset.concept,
      });
    });
    return selected;
  }

  function renderAnalysis(data) {
    analysisData = data;
    assignmentTextCache = data.assignment_text || assignmentText.value.trim();
    analysisSummary.textContent = data.summary || "";

    coverageGrid.innerHTML = "";
    (data.syllabus_coverage || []).forEach((topic) => {
      const card = document.createElement("article");
      card.className = "coverage-card " + (topic.covered ? "covered" : "uncovered");

      const head = document.createElement("div");
      head.className = "coverage-card-head";
      head.innerHTML =
        `<span class="coverage-status">${topic.covered ? "Covered" : "Not covered"}</span>` +
        `<h4>${topic.label}</h4>`;
      card.appendChild(head);

      const conceptsWrap = document.createElement("div");
      conceptsWrap.className = "coverage-concepts";

      if (topic.covered && topic.concepts.length) {
        topic.concepts.forEach((concept, idx) => {
          const label = document.createElement("label");
          label.className = "concept-chip covered";
          const id = `c-${topic.topic_id}-${idx}`;
          label.innerHTML =
            `<input type="checkbox" class="concept-check" id="${id}" ` +
            `data-topic-id="${topic.topic_id}" checked />` +
            `<span>${escapeHtml(concept)}</span>`;
          const input = label.querySelector("input");
          input.dataset.concept = concept;
          conceptsWrap.appendChild(label);
        });
      } else if (!topic.covered) {
        const empty = document.createElement("p");
        empty.className = "no-concepts";
        empty.textContent = "No matching concepts in assignment";
        conceptsWrap.appendChild(empty);
      }

      card.appendChild(conceptsWrap);
      coverageGrid.appendChild(card);
    });

    coverageGrid.querySelectorAll(".concept-check").forEach((cb) => {
      cb.addEventListener("change", updateGenerateButton);
    });

    const outItems = data.out_of_syllabus_concepts || [];
    if (outItems.length) {
      outOfSyllabus.classList.remove("hidden");
      outList.innerHTML = "";
      outItems.forEach((item) => {
        const li = document.createElement("li");
        li.className = "out-chip";
        li.innerHTML =
          `<strong>${escapeHtml(item.concept)}</strong>` +
          (item.reason ? `<span>${escapeHtml(item.reason)}</span>` : "");
        outList.appendChild(li);
      });
    } else {
      outOfSyllabus.classList.add("hidden");
    }

    analysisSection.classList.remove("hidden");
    resultSection.classList.add("hidden");
    updateGenerateButton();
    analysisSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function parseFileList(text) {
    return (text || "")
      .split(/[\n,]+/)
      .map((line) => line.trim().replace(/\\/g, "/"))
      .filter(Boolean);
  }

  function renderPathList(listEl, paths) {
    listEl.innerHTML = "";
    (paths || []).forEach((f) => {
      const li = document.createElement("li");
      li.textContent = f;
      listEl.appendChild(li);
    });
  }

  function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }

  analyzeBtn.addEventListener("click", async () => {
    hideError();
    setAnalyzeLoading(true);

    try {
      const payload = await getAssignmentPayload();
      const options =
        payload.type === "json"
          ? {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload.body),
            }
          : { method: "POST", body: payload.body };

      const res = await fetch("/analyze", options);
      const data = await res.json();

      if (!res.ok) {
        showError(data.error || "Analysis failed.");
        return;
      }

      if (inputMode === "doc" && data.assignment_text) {
        extractedPreview.textContent = data.assignment_text.slice(0, 1500) +
          (data.assignment_text.length > 1500 ? "\n\n…" : "");
        extractedPreviewWrap.classList.remove("hidden");
      }

      renderAnalysis(data);
    } catch (err) {
      showError(err.message || "Network error — is the server running?");
    } finally {
      setAnalyzeLoading(false);
    }
  });

  function renderFileList() {
    if (!currentPreview) return;
    const files = currentPreview[activeFolder] || {};
    const paths = Object.keys(files).sort();
    fileList.innerHTML = "";

    paths.forEach((path) => {
      const btn = document.createElement("button");
      btn.type = "button";
      const isStudent = (window._studentFiles || []).some(
        (sf) => path.endsWith("/" + sf) || path.endsWith(sf)
      );
      btn.className = "file-item" + (path === activeFile ? " active" : "");
      if (isStudent) btn.classList.add("student-file");
      btn.textContent = path.split("/").slice(1).join("/") || path;
      btn.dataset.path = path;
      btn.addEventListener("click", () => selectFile(path));
      fileList.appendChild(btn);
    });

    if (paths.length && (!activeFile || !files[activeFile])) {
      selectFile(paths[0]);
    }
  }

  function selectFile(path) {
    activeFile = path;
    filePreviewHeader.textContent = path;
    fileContent.textContent = currentPreview[activeFolder][path] || "";
    fileList.querySelectorAll(".file-item").forEach((el) => {
      el.classList.toggle("active", el.dataset.path === path);
    });
  }

  function showResult(data) {
    currentPreview = data.preview;
    activeFolder = "prefilled";
    activeFile = null;
    window._studentFiles = data.student_files || [];

    resultTitle.textContent = data.title;
    resultMeta.textContent = data.domain
      ? `Slug: ${data.slug} · Domain: ${data.domain}`
      : `Slug: ${data.slug}`;

    structureRationale.textContent = data.file_structure_rationale || "";
    syllabusTopicsList.innerHTML = "";
    (data.syllabus_topic_labels || data.syllabus_topics || []).forEach((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      syllabusTopicsList.appendChild(li);
    });
    studentFilesList.innerHTML = "";
    renderPathList(studentFilesList, data.student_files || []);
    scaffoldFilesList.innerHTML = "";
    renderPathList(scaffoldFilesList, data.scaffold_files || []);

    downloadBtn.href = `/download/${data.slug}`;
    resultSection.classList.remove("hidden");
    folderTabs.querySelectorAll(".tab").forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.folder === activeFolder);
    });
    renderFileList();
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  folderTabs.addEventListener("click", (e) => {
    const tab = e.target.closest(".tab");
    if (!tab) return;
    activeFolder = tab.dataset.folder;
    activeFile = null;
    folderTabs.querySelectorAll(".tab").forEach((t) => {
      t.classList.toggle("active", t === tab);
    });
    renderFileList();
  });

  generateBtn.addEventListener("click", async () => {
    hideError();
    const selected = getSelectedConcepts();
    if (!selected.length) {
      showError("Select at least one covered concept.");
      return;
    }

    setGenerateLoading(true);
    generateBtn.disabled = true;

    try {
      const res = await fetch("/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          selected_concepts: selected,
          assignment_text: assignmentTextCache,
          domain: domainInput.value.trim(),
          question_title: questionTitleInput.value.trim(),
          student_files: parseFileList(filesToImplement.value),
          scaffold_files: parseFileList(filesScaffold.value),
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        showError(data.error || "Generation failed.");
        return;
      }
      showResult(data);
    } catch (err) {
      showError("Network error — is the server running?");
    } finally {
      setGenerateLoading(false);
      updateGenerateButton();
    }
  });
})();
