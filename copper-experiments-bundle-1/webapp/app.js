const COLORS = {
  reference: "#e7298a",
  training_site_self_match: "#1b9e77",
  known_deposit_rediscovered: "#7570b3",
  candidate_needs_manual_review: "#d95f02",
};

const LABELS = {
  reference: "Reference deposit (trained on)",
  training_site_self_match: "Self-match (near a reference site)",
  known_deposit_rediscovered: "Known deposit, re-discovered",
  candidate_needs_manual_review: "Candidate — needs manual review",
};

const map = L.map("map", { zoomControl: true }).setView([36.5, -112.5], 6);

L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  subdomains: "abcd",
  maxZoom: 19,
}).addTo(map);

const layerGroups = {
  reference: L.layerGroup().addTo(map),
  training_site_self_match: L.layerGroup().addTo(map),
  known_deposit_rediscovered: L.layerGroup().addTo(map),
  candidate_needs_manual_review: L.layerGroup().addTo(map),
};

function marker(latlng, status, radius) {
  return L.circleMarker(latlng, {
    radius: radius,
    color: "#000",
    weight: 1,
    opacity: 0.6,
    fillColor: COLORS[status],
    fillOpacity: 0.9,
  });
}

function popupHtml(title, status, rows) {
  const rowsHtml = rows.map((r) => `<div class="popup-row">${r}</div>`).join("");
  return `<div class="popup-title">${title}</div>
    <span class="badge" style="background:${COLORS[status]}22;color:${COLORS[status]}">${LABELS[status]}</span>
    ${rowsHtml}`;
}

const stats = { reference: 0, training_site_self_match: 0, known_deposit_rediscovered: 0, candidate_needs_manual_review: 0 };
const candidateCards = [];

fetch("data/reference_sites.geojson")
  .then((r) => r.json())
  .then((fc) => {
    fc.features.forEach((f) => {
      const [lon, lat] = f.geometry.coordinates;
      const p = f.properties;
      stats.reference++;
      marker([lat, lon], "reference", 9)
        .bindPopup(popupHtml(p.name, "reference", [
          `${p.state} &middot; ${lat.toFixed(4)}, ${lon.toFixed(4)}`,
          p.note,
        ]))
        .addTo(layerGroups.reference);
    });
    renderStats();
  });

fetch("data/conus_wide_prospects.geojson")
  .then((r) => r.json())
  .then((fc) => {
    fc.features.forEach((f) => {
      const [lon, lat] = f.geometry.coordinates;
      const p = f.properties;
      stats[p.status]++;

      const rows = [`score ${p.score.toFixed(4)} &middot; ${lat.toFixed(4)}, ${lon.toFixed(4)}`];
      if (p.status !== "candidate_needs_manual_review") {
        rows.push(`Nearest known: <b>${p.nearest_known}</b> (${p.km_to_known} km)`);
      } else if (p.region_note) {
        rows.push(p.region_note);
      }
      rows.push(`<span style="opacity:0.6">chip: ${p.chip_id}</span>`);

      const radius = p.status === "candidate_needs_manual_review" ? 7 : 6;
      const title = p.status === "candidate_needs_manual_review" ? "Unlabeled candidate" : p.nearest_known;
      marker([lat, lon], p.status, radius)
        .bindPopup(popupHtml(title, p.status, rows))
        .addTo(layerGroups[p.status]);

      if (p.status === "candidate_needs_manual_review") {
        candidateCards.push({ lat, lon, score: p.score, note: p.region_note || "" });
      }
    });
    candidateCards.sort((a, b) => b.score - a.score);
    renderStats();
    renderList();
  });

function renderStats() {
  document.getElementById("stats").innerHTML = Object.entries(stats)
    .map(([k, v]) => `<div class="stat-row"><span>${LABELS[k]}</span><b>${v}</b></div>`)
    .join("");
}

function renderList() {
  const list = document.getElementById("list");
  list.innerHTML = candidateCards
    .slice(0, 12)
    .map(
      (c, i) => `<div class="card" data-idx="${i}">
        <div class="name">#${i + 1} &middot; score ${c.score.toFixed(4)}</div>
        <div class="meta">${c.lat.toFixed(3)}, ${c.lon.toFixed(3)} &mdash; ${c.note ? c.note.slice(0, 90) + (c.note.length > 90 ? "…" : "") : "no region note"}</div>
      </div>`
    )
    .join("");
  list.querySelectorAll(".card").forEach((el) => {
    el.addEventListener("click", () => {
      const c = candidateCards[Number(el.dataset.idx)];
      map.flyTo([c.lat, c.lon], 10, { duration: 0.6 });
    });
  });
}

document.querySelectorAll('input[data-layer]').forEach((input) => {
  input.addEventListener("change", () => {
    const key = input.dataset.layer;
    if (input.checked) {
      map.addLayer(layerGroups[key]);
    } else {
      map.removeLayer(layerGroups[key]);
    }
  });
});
