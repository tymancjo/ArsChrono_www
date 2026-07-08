(function () {
  "use strict";

  var state = { featured: [null, null, null], grid: [], new: [] };
  var selected = null; // {section, index}

  var featuredSlots = document.querySelectorAll("#featured-panel .slot");
  var gridList = document.getElementById("grid-list");
  var newList = document.getElementById("new-list");
  var statusEl = document.getElementById("status");

  function setStatus(msg, kind) {
    statusEl.textContent = msg || "";
    statusEl.className = kind || "";
  }

  function loadState() {
    fetch("/api/state")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        state.featured = [data.featured[0] || null, data.featured[1] || null, data.featured[2] || null];
        state.grid = data.grid;
        state.new = data.new;
        selected = null;
        render();
        setStatus("Loaded.", "ok");
      })
      .catch(function (err) { setStatus("Load failed: " + err, "error"); });
  }

  function makeCard(item, section, index, isNew) {
    var card = document.createElement("div");
    card.className = "card" + (isNew ? " new" : "");
    card.draggable = true;
    card.dataset.section = section;
    card.dataset.index = index;

    if (isSelected(section, index)) card.classList.add("selected");

    if (isNew) {
      var badge = document.createElement("div");
      badge.className = "badge";
      badge.textContent = "New";
      card.appendChild(badge);
    }

    var img = document.createElement("img");
    img.src = "/pictures/" + encodeURIComponent(item.file);
    img.alt = item.alt;
    card.appendChild(img);

    var input = document.createElement("input");
    input.type = "text";
    input.value = item.alt;
    input.addEventListener("input", function () { item.alt = input.value; });
    input.addEventListener("click", function (e) { e.stopPropagation(); });
    input.addEventListener("dragstart", function (e) { e.preventDefault(); e.stopPropagation(); });
    card.appendChild(input);

    card.addEventListener("click", function () { onCardClick(section, index); });
    card.addEventListener("dragstart", function (e) {
      e.dataTransfer.setData("text/plain", JSON.stringify({ section: section, index: index }));
    });
    card.addEventListener("dragover", function (e) { e.preventDefault(); card.classList.add("drag-over"); });
    card.addEventListener("dragleave", function () { card.classList.remove("drag-over"); });
    card.addEventListener("drop", function (e) {
      e.preventDefault();
      card.classList.remove("drag-over");
      var src = JSON.parse(e.dataTransfer.getData("text/plain"));
      moveItem(src, { section: section, index: index });
    });

    return card;
  }

  function isSelected(section, index) {
    return selected && selected.section === section && selected.index === index;
  }

  function onCardClick(section, index) {
    if (!selected) {
      selected = { section: section, index: index };
      render();
      return;
    }
    if (selected.section === section && selected.index === index) {
      selected = null;
      render();
      return;
    }
    var src = selected;
    selected = null;
    moveItem(src, { section: section, index: index });
  }

  function render() {
    featuredSlots.forEach(function (slot) {
      var idx = Number(slot.dataset.index);
      slot.innerHTML = "";
      var item = state.featured[idx];
      if (item) {
        slot.classList.remove("empty");
        slot.appendChild(makeCard(item, "featured", idx, false));
      } else {
        slot.classList.add("empty");
      }
      slot.ondragover = function (e) { e.preventDefault(); };
      slot.ondrop = function (e) {
        e.preventDefault();
        if (e.target !== slot) return; // let card handle its own drop
        var src = JSON.parse(e.dataTransfer.getData("text/plain"));
        moveItem(src, { section: "featured", index: idx });
      };
      slot.onclick = function (e) {
        if (e.target !== slot) return; // card already handled the click
        if (item) return;
        if (!selected) return;
        var src = selected;
        selected = null;
        moveItem(src, { section: "featured", index: idx });
      };
    });

    gridList.innerHTML = "";
    state.grid.forEach(function (item, i) {
      gridList.appendChild(makeCard(item, "grid", i, false));
    });

    newList.innerHTML = "";
    state.new.forEach(function (item, i) {
      newList.appendChild(makeCard(item, "new", i, true));
    });
  }

  function removeFromSection(section, index) {
    if (section === "featured") {
      var item = state.featured[index];
      state.featured[index] = null;
      return item;
    }
    return state[section].splice(index, 1)[0];
  }

  function insertIntoSection(section, index, item) {
    if (section === "featured") {
      var old = state.featured[index];
      state.featured[index] = item;
      if (old) state.grid.unshift(old);
      return;
    }
    var arr = state[section];
    var at = Math.max(0, Math.min(index, arr.length));
    arr.splice(at, 0, item);
  }

  function moveItem(src, dst) {
    if (!src || !dst) return;
    if (src.section === dst.section && src.index === dst.index) return;

    // featured <-> featured is a simple slot swap
    if (src.section === "featured" && dst.section === "featured") {
      var a = state.featured[src.index];
      var b = state.featured[dst.index];
      state.featured[src.index] = b;
      state.featured[dst.index] = a;
      render();
      return;
    }

    // same-array reorder (grid<->grid or new<->new): splice-move to keep indices correct
    if (src.section === dst.section) {
      var arr = state[src.section];
      var item = arr.splice(src.index, 1)[0];
      var at = dst.index;
      if (src.index < dst.index) at -= 1;
      arr.splice(at, 0, item);
      render();
      return;
    }

    var moved = removeFromSection(src.section, src.index);
    if (!moved) { render(); return; }
    insertIntoSection(dst.section, dst.index, moved);
    render();
  }

  document.getElementById("reload-btn").addEventListener("click", function () {
    loadState();
  });

  document.getElementById("save-btn").addEventListener("click", function () {
    if (state.featured.some(function (s) { return !s; })) {
      setStatus("Fill all 3 featured slots before saving.", "error");
      return;
    }
    setStatus("Saving...", "");
    fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ featured: state.featured, grid: state.grid }),
    })
      .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, data: data }; }); })
      .then(function (res) {
        if (res.ok && res.data.ok) {
          setStatus("Saved to src/03-galeria.md", "ok");
        } else {
          setStatus("Save failed: " + (res.data.error || "unknown error"), "error");
        }
      })
      .catch(function (err) { setStatus("Save failed: " + err, "error"); });
  });

  loadState();
})();
