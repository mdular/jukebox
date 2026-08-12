"use strict";

const elements = {
  searchForm: document.querySelector("#search-form"),
  searchQuery: document.querySelector("#search-query"),
  referenceForm: document.querySelector("#reference-form"),
  spotifyReference: document.querySelector("#spotify-reference"),
  status: document.querySelector("#status"),
  results: document.querySelector("#results"),
  review: document.querySelector("#review"),
  selectedArtwork: document.querySelector("#selected-artwork"),
  selectedKind: document.querySelector("#selected-kind"),
  selectedPrimary: document.querySelector("#selected-primary"),
  selectedSecondary: document.querySelector("#selected-secondary"),
  selectedUri: document.querySelector("#selected-uri"),
  selectedSpotifyLink: document.querySelector("#selected-spotify-link"),
  artworkWarning: document.querySelector("#artwork-warning"),
  resolutionWarning: document.querySelector("#resolution-warning"),
  createPreview: document.querySelector("#create-preview"),
  previewSection: document.querySelector("#preview-section"),
  preview: document.querySelector("#preview"),
  download: document.querySelector("#download"),
  makeAnother: document.querySelector("#make-another"),
};

let selectedItem = null;
let previewObjectUrl = null;

elements.searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearStatus();
  try {
    const query = elements.searchQuery.value.trim();
    const payload = await requestJson(`/api/search?q=${encodeURIComponent(query)}`);
    showResults(payload.items);
  } catch (error) {
    showError(error);
  }
});

elements.referenceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearStatus();
  try {
    const payload = await requestJson("/api/resolve", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({reference: elements.spotifyReference.value}),
    });
    selectItem(payload.item);
  } catch (error) {
    showError(error);
  }
});

elements.createPreview.addEventListener("click", async () => {
  if (!selectedItem || !selectedItem.artwork) return;
  clearStatus();
  elements.createPreview.disabled = true;
  try {
    const response = await fetch("/api/render", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({uri: selectedItem.uri}),
    });
    if (!response.ok) throw await responseError(response);
    const blob = await response.blob();
    releasePreview();
    previewObjectUrl = URL.createObjectURL(blob);
    elements.preview.src = previewObjectUrl;
    elements.download.href = previewObjectUrl;
    elements.download.download = suggestedFilename(response.headers.get("Content-Disposition"));
    elements.previewSection.hidden = false;
    elements.previewSection.scrollIntoView({behavior: "smooth", block: "start"});
  } catch (error) {
    showError(error);
  } finally {
    elements.createPreview.disabled = !selectedItem?.artwork;
  }
});

elements.makeAnother.addEventListener("click", () => {
  releasePreview();
  selectedItem = null;
  elements.review.hidden = true;
  elements.previewSection.hidden = true;
  document.querySelector("#discovery").scrollIntoView({behavior: "smooth", block: "start"});
  elements.searchQuery.focus();
});

window.addEventListener("beforeunload", releasePreview);

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) throw await responseError(response);
  return response.json();
}

async function responseError(response) {
  try {
    const payload = await response.json();
    return new Error(payload.message || "The request failed.");
  } catch (_error) {
    return new Error("The request failed.");
  }
}

function showResults(items) {
  elements.results.replaceChildren();
  if (items.length === 0) {
    elements.status.textContent = "No Spotify results found.";
    return;
  }

  const labels = {track: "Tracks", album: "Albums", playlist: "Playlists"};
  for (const kind of ["track", "album", "playlist"]) {
    const matches = items.filter((item) => item.kind === kind);
    if (matches.length === 0) continue;
    const group = document.createElement("section");
    group.className = "result-group";
    const heading = document.createElement("h3");
    heading.textContent = labels[kind];
    group.append(heading);
    const list = document.createElement("ul");
    list.className = "result-list";
    for (const item of matches) list.append(resultRow(item));
    group.append(list);
    elements.results.append(group);
  }
}

function resultRow(item) {
  const row = document.createElement("li");
  if (item.artwork) {
    const artwork = document.createElement("img");
    artwork.src = item.artwork.url;
    artwork.alt = "";
    artwork.loading = "lazy";
    row.append(artwork);
  }
  const details = document.createElement("div");
  const primary = document.createElement("strong");
  primary.textContent = item.primary_label;
  details.append(primary);
  if (item.secondary_label) {
    const secondary = document.createElement("span");
    secondary.textContent = item.secondary_label;
    details.append(secondary);
  }
  const spotify = document.createElement("a");
  spotify.href = item.external_url;
  spotify.target = "_blank";
  spotify.rel = "noopener noreferrer";
  spotify.textContent = "Open in Spotify";
  details.append(spotify);
  row.append(details);
  const choose = document.createElement("button");
  choose.type = "button";
  choose.textContent = "Choose";
  choose.addEventListener("click", () => selectItem(item));
  row.append(choose);
  return row;
}

function selectItem(item) {
  releasePreview();
  selectedItem = item;
  elements.previewSection.hidden = true;
  elements.selectedKind.textContent = item.kind;
  elements.selectedPrimary.textContent = item.primary_label;
  elements.selectedSecondary.textContent = item.secondary_label || "";
  elements.selectedSecondary.hidden = !item.secondary_label;
  elements.selectedUri.textContent = item.uri;
  elements.selectedSpotifyLink.href = item.external_url;
  elements.selectedArtwork.hidden = !item.artwork;
  elements.artworkWarning.hidden = Boolean(item.artwork);
  elements.resolutionWarning.hidden = !isLowResolution(item.artwork);
  elements.createPreview.disabled = !item.artwork;
  if (item.artwork) {
    elements.selectedArtwork.src = item.artwork.url;
    elements.selectedArtwork.alt = `Spotify artwork for ${item.primary_label}`;
  } else {
    elements.selectedArtwork.removeAttribute("src");
    elements.selectedArtwork.alt = "";
  }
  elements.review.hidden = false;
  elements.review.scrollIntoView({behavior: "smooth", block: "start"});
}

function suggestedFilename(disposition) {
  if (!disposition) return "card.png";
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (encoded) return decodeURIComponent(encoded[1]);
  const plain = disposition.match(/filename="?([^";]+)"?/i);
  return plain ? plain[1] : "card.png";
}

function isLowResolution(artwork) {
  if (!artwork || !Number.isFinite(artwork.width) || !Number.isFinite(artwork.height)) {
    return false;
  }
  return Math.min(404 / artwork.width, 453 / artwork.height) > 1;
}

function releasePreview() {
  if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl);
  previewObjectUrl = null;
  elements.preview.removeAttribute("src");
  elements.download.removeAttribute("href");
}

function clearStatus() {
  elements.status.className = "";
  elements.status.textContent = "";
}

function showError(error) {
  elements.status.className = "error";
  elements.status.textContent = error instanceof Error ? error.message : "The request failed.";
}
