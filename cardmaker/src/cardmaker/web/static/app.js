"use strict";

const EXPECTED_CARD_WIDTH = "1200";
const EXPECTED_CARD_HEIGHT = "756";

const elements = {
  discovery: document.querySelector("#discovery"),
  searchForm: document.querySelector("#search-form"),
  searchQuery: document.querySelector("#search-query"),
  referenceForm: document.querySelector("#reference-form"),
  spotifyReference: document.querySelector("#spotify-reference"),
  discoveryStatus: document.querySelector("#status"),
  results: document.querySelector("#results"),
  review: document.querySelector("#review"),
  cardPreview: document.querySelector("#card-preview"),
  selectedKind: document.querySelector("#selected-kind"),
  selectedPrimary: document.querySelector("#selected-primary"),
  selectedSecondary: document.querySelector("#selected-secondary"),
  selectedUri: document.querySelector("#selected-uri"),
  selectedSpotifyLink: document.querySelector("#selected-spotify-link"),
  artworkWarning: document.querySelector("#artwork-warning"),
  resolutionWarning: document.querySelector("#resolution-warning"),
  downloadPng: document.querySelector("#download-png"),
  previewStatus: document.querySelector("#preview-status"),
  makeAnother: document.querySelector("#make-another"),
};

let selectedItem = null;
let activeRenderController = null;
let previewObjectUrl = null;
let previewFilename = null;

elements.searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearDiscoveryStatus();
  try {
    const query = elements.searchQuery.value.trim();
    const payload = await requestJson(`/api/search?q=${encodeURIComponent(query)}`);
    showResults(payload.items);
  } catch (error) {
    showDiscoveryError(error);
  }
});

elements.referenceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearDiscoveryStatus();
  try {
    const payload = await requestJson("/api/resolve", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({reference: elements.spotifyReference.value}),
    });
    selectItem(payload.item);
  } catch (error) {
    showDiscoveryError(error);
  }
});

elements.downloadPng.addEventListener("click", () => {
  if (!previewObjectUrl || !previewFilename) return;

  const downloadLink = document.createElement("a");
  try {
    downloadLink.href = previewObjectUrl;
    downloadLink.download = previewFilename;
    downloadLink.hidden = true;
    document.body.append(downloadLink);
    downloadLink.click();
    elements.previewStatus.textContent = "Download started. Review the PNG before printing.";
  } finally {
    downloadLink.remove();
  }
});

elements.makeAnother.addEventListener("click", () => {
  abortActiveRender();
  releasePreview();
  selectedItem = null;
  clearPreviewStatus();
  clearSelectionReview();
  elements.downloadPng.disabled = true;
  elements.review.hidden = true;
  elements.discovery.scrollIntoView({behavior: "smooth", block: "start"});
  elements.searchQuery.focus();
});

window.addEventListener("beforeunload", () => {
  abortActiveRender();
  releasePreview();
});

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
    elements.discoveryStatus.textContent = "No Spotify results found.";
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
  abortActiveRender();
  releasePreview();
  selectedItem = item;
  clearPreviewStatus();
  elements.selectedKind.textContent = item.kind;
  elements.selectedPrimary.textContent = item.primary_label;
  elements.selectedSecondary.textContent = item.secondary_label || "";
  elements.selectedSecondary.hidden = !item.secondary_label;
  elements.selectedUri.textContent = item.uri;
  elements.selectedSpotifyLink.href = item.external_url;
  elements.artworkWarning.hidden = Boolean(item.artwork);
  elements.resolutionWarning.hidden = !isLowResolution(item.artwork);
  elements.downloadPng.disabled = true;
  elements.review.hidden = false;
  elements.review.scrollIntoView({behavior: "smooth", block: "start"});
  if (item.artwork) void renderPreview(item.uri);
}

async function renderPreview(selectedUri) {
  const controller = new AbortController();
  activeRenderController = controller;
  elements.previewStatus.textContent = "Rendering and verifying the preview…";

  try {
    const response = await fetch("/api/render", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({uri: selectedUri}),
      signal: controller.signal,
    });
    if (!response.ok) throw await responseError(response);

    requireVerifiedResponse(response, selectedUri);
    const blob = await response.blob();
    if (controller.signal.aborted || !isCurrentSelection(selectedUri)) return;
    if (blob.type.toLowerCase() !== "image/png") throw integrityError();

    previewObjectUrl = URL.createObjectURL(blob);
    previewFilename = suggestedFilename(response.headers.get("Content-Disposition"));
    elements.cardPreview.src = previewObjectUrl;
    elements.cardPreview.hidden = false;
    elements.downloadPng.disabled = false;
    elements.previewStatus.textContent = "Preview verified and ready to download.";
  } catch (error) {
    releasePreview();
    if (!isAbortError(error) && isCurrentSelection(selectedUri)) {
      showPreviewError(error);
    }
  } finally {
    if (activeRenderController === controller) activeRenderController = null;
  }
}

function requireVerifiedResponse(response, expectedUri) {
  const contentType = (response.headers.get("Content-Type") || "")
    .split(";", 1)[0]
    .trim()
    .toLowerCase();
  const responseUri = response.headers.get("X-Cardmaker-Spotify-URI");
  const width = response.headers.get("X-Cardmaker-Width");
  const height = response.headers.get("X-Cardmaker-Height");
  if (
    contentType !== "image/png" ||
    responseUri !== expectedUri ||
    responseUri !== selectedItem?.uri ||
    responseUri !== elements.selectedUri.textContent ||
    width !== EXPECTED_CARD_WIDTH ||
    height !== EXPECTED_CARD_HEIGHT
  ) {
    throw integrityError();
  }
}

function integrityError() {
  return new Error("The card response failed an integrity check. Nothing was downloaded.");
}

function suggestedFilename(disposition) {
  if (!disposition) return "card.png";
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (encoded) {
    try {
      const decoded = decodeURIComponent(encoded[1]).trim();
      if (decoded) return decoded;
    } catch (_error) {
      // Fall through to a usable plain filename when one is present.
    }
  }
  const plain = disposition.match(/filename="?([^";]+)"?/i);
  return plain && plain[1].trim() ? plain[1].trim() : "card.png";
}

function isLowResolution(artwork) {
  if (!artwork || !Number.isFinite(artwork.width) || !Number.isFinite(artwork.height)) {
    return false;
  }
  return Math.min(404 / artwork.width, 453 / artwork.height) > 1;
}

function isCurrentSelection(uri) {
  return selectedItem !== null && selectedItem.uri === uri;
}

function isAbortError(error) {
  return Boolean(error && typeof error === "object" && error.name === "AbortError");
}

function abortActiveRender() {
  if (activeRenderController) activeRenderController.abort();
  activeRenderController = null;
}

function releasePreview() {
  if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl);
  previewObjectUrl = null;
  previewFilename = null;
  elements.cardPreview.removeAttribute("src");
  elements.cardPreview.hidden = true;
}

function clearSelectionReview() {
  elements.selectedKind.textContent = "";
  elements.selectedPrimary.textContent = "";
  elements.selectedSecondary.textContent = "";
  elements.selectedUri.textContent = "";
  elements.selectedSpotifyLink.removeAttribute("href");
  elements.artworkWarning.hidden = true;
  elements.resolutionWarning.hidden = true;
}

function clearDiscoveryStatus() {
  elements.discoveryStatus.className = "";
  elements.discoveryStatus.textContent = "";
}

function clearPreviewStatus() {
  elements.previewStatus.className = "";
  elements.previewStatus.textContent = "";
}

function showDiscoveryError(error) {
  elements.discoveryStatus.className = "error";
  elements.discoveryStatus.textContent = errorMessage(error);
}

function showPreviewError(error) {
  elements.previewStatus.className = "error";
  elements.previewStatus.textContent = errorMessage(error);
}

function errorMessage(error) {
  return error instanceof Error ? error.message : "The request failed.";
}
