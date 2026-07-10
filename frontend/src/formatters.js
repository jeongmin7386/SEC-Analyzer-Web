export function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }

  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: digits,
  }).format(Number(value));
}

export function formatCompact(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }

  return new Intl.NumberFormat("ko-KR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(Number(value));
}

export function formatMoney(value, currency = "USD") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }

  const number = Number(value);
  const abs = Math.abs(number);

  if (currency === "KRW") {
    if (abs >= 1_0000_0000_0000) {
      return `${formatNumber(number / 1_0000_0000_0000, 2)}조 원`;
    }
    if (abs >= 1_0000_0000) {
      return `${formatNumber(number / 1_0000_0000, 1)}억 원`;
    }
    return `${formatNumber(number, 0)}원`;
  }

  if (abs >= 1_000_000_000) {
    return `$${formatNumber(number / 1_000_000_000, 2)}B`;
  }
  if (abs >= 1_000_000) {
    return `$${formatNumber(number / 1_000_000, 1)}M`;
  }
  return `$${formatNumber(number, 0)}`;
}

export function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }

  return `${formatNumber(Number(value) * 100, 2)}%`;
}

export function formatSigned(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }

  const number = Number(value);
  const prefix = number > 0 ? "+" : "";
  return `${prefix}${formatNumber(number, digits)}`;
}

export function shortDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value).slice(0, 10);
  }
  return `${date.getMonth() + 1}/${date.getDate()}`;
}
