const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  const payload = await readJson(response);

  if (!response.ok) {
    const detail = payload?.detail || "요청을 처리하지 못했습니다.";
    throw new Error(detail);
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
