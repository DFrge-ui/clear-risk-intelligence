"use strict";
const LANG = document.documentElement.lang === "ru" ? "ru" : "en";
const LOCALE = LANG === "ru" ? "ru-RU" : "en-GB";
const messages = JSON.parse(
  document.getElementById("translations").textContent,
);
function t(message, values = {}) {
  let result = messages[message] || message;
  for (const [key, value] of Object.entries(values))
    result = result.replaceAll(`{${key}}`, String(value));
  return result;
}
function translateError(message) {
  if (LANG !== "ru") return message;
  if (messages[message]) return messages[message];
  const patterns = [
    [/^Exact duplicate of (.+) removed\.$/, "Exact duplicate of {id} removed."],
    [
      /^Conflicting duplicate ID (.+); first valid record retained\.$/,
      "Conflicting duplicate ID {id}; first valid record retained.",
    ],
    [
      /^Missing required columns: (.+)\. Download the sample CSV for the expected format\.$/,
      "Missing required columns: {id}. Download the sample CSV for the expected format.",
    ],
  ];
  for (const [pattern, key] of patterns) {
    const match = message.match(pattern);
    if (match) return t(key, { id: match[1] });
  }
  const prefix = "No valid records found. ";
  if (message.startsWith(prefix))
    return (
      t("No valid records found.") +
      " " +
      translateError(message.slice(prefix.length))
    );
  return message;
}
