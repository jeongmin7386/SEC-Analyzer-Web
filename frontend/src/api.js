const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  const payload = await readJson(response);

  if (!response.ok) {
    throw apiError(payload);
  }

  return payload;
}

export async function apiPost(path, body) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: JSON.stringify(body),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });
  const payload = await readJson(response);

  if (!response.ok) {
    throw apiError(payload);
  }

  return payload;
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function errorMessage(payload) {
  const detail = payload?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (detail?.message) {
    return detail.message;
  }
  return "Request failed.";
}

function apiError(payload) {
  const error = new Error(errorMessage(payload));
  error.detail = payload?.detail;
  return error;
}
