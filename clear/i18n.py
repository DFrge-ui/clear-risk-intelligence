"""Shared source-string translations for Jinja, browser UI and report prose."""
import json
from functools import lru_cache
from pathlib import Path

from flask import request


SUPPORTED_LANGUAGES = ("en", "ru", "de")


@lru_cache(maxsize=3)
def messages_for(lang):
    if lang not in ("ru", "de"):
        return {}
    return json.loads((Path(__file__).parent / "locales" / f"{lang}.json").read_text(encoding="utf-8"))


def format_amount(value, lang):
    formatted = f"{value:,.2f}"
    if lang == "ru":
        return formatted.replace(",", " ").replace(".", ",")
    if lang == "de":
        return formatted.translate(str.maketrans({",": ".", ".": ","}))
    return formatted


def language():
    value = request.args.get("lang", request.cookies.get("clear_language", "en"))
    return value if value in SUPPORTED_LANGUAGES else "en"


def translate(message, lang=None, **values):
    lang = lang or language()
    translated = messages_for(lang).get(message, message)
    for key, value in values.items():
        translated = translated.replace("{" + key + "}", str(value))
    return translated


def localize_summary(summary, as_of, lang):
    """Translate prose from already computed facts; do not recalculate any metric."""
    if lang not in ("ru", "de"):
        return summary
    result = summary.copy()
    m = summary["metrics"]
    if not m["total"]:
        result["narrative"] = translate("No incidents match these filters. Broaden the selection to generate a management summary.", lang)
        return result
    top = summary["categories"][0]
    money = lambda value: format_amount(value, lang)
    if lang == "de":
        result["narrative"] = (
            f"Zum {as_of} umfasst die Auswahl {m['total']} Vorfälle, davon sind {m['active']} aktiv. "
            f"Der erfasste Verlust beträgt {money(m['loss'])} EUR. "
            f"Bei {m['flagged']} Vorfällen wurde mindestens eine Prüfregel ausgelöst; "
            f"{m['critical']} aktive Fälle sind kritisch. "
            f"Der höchste erfasste Verlust entfällt auf die Kategorie {translate(top['name'], lang)} "
            f"({money(top['loss'])} EUR). "
            f"{m['aging']} aktive Fälle sind älter als 14 Tage; bei {m['unassigned']} fehlt eine Zuständigkeit."
        )
        actions = []
        if m["critical"]:
            actions.append(f"Prüfen Sie die kritischen aktiven Fälle ({m['critical']}) und legen Sie den nächsten Schritt fest.")
        if m["unassigned"]:
            actions.append(f"Weisen Sie den aktiven Fällen ohne Zuständigkeit ({m['unassigned']}) eine verantwortliche Person zu.")
        if m["aging"]:
            actions.append(f"Prüfen Sie den Fortschritt der aktiven Fälle, die älter als 14 Tage sind ({m['aging']}).")
        if m["flagged"] and not actions:
            actions.append("Gleichen Sie die markierten Verlustbeträge mit den Quelldatensätzen ab.")
        if not actions:
            actions.append("Keine Prüfregeln ausgelöst. Setzen Sie die reguläre Kontrolle fort; dies garantiert kein niedriges Risiko.")
        result["actions"] = actions
        return result
    result["narrative"] = (
        f"На {as_of} в выборке {m['total']} инцидентов, из них активных — {m['active']}. "
        f"Зафиксированная сумма потерь — {money(m['loss'])} EUR. "
        f"Хотя бы одно правило проверки сработало для {m['flagged']} инцидентов; "
        f"критических активных случаев — {m['critical']}. "
        f"Наибольшая сумма потерь в категории «{translate(top['name'], lang)}» ({money(top['loss'])} EUR). "
        f"Активных случаев старше 14 дней — {m['aging']}, без ответственного — {m['unassigned']}."
    )
    actions = []
    if m["critical"]:
        actions.append(f"Проверьте критические активные случаи ({m['critical']}) и определите следующий шаг.")
    if m["unassigned"]:
        actions.append(f"Назначьте ответственных для активных случаев без владельца ({m['unassigned']}).")
    if m["aging"]:
        actions.append(f"Проверьте ход работы по активным случаям старше 14 дней ({m['aging']}).")
    if m["flagged"] and not actions:
        actions.append("Сверьте отмеченные суммы потерь с исходными записями.")
    if not actions:
        actions.append("Правила проверки не сработали. Продолжайте обычный контроль: это не гарантирует низкий риск.")
    result["actions"] = actions
    return result


def init_app(app):
    @app.context_processor
    def localization_context():
        lang = language()
        return {"lang": lang, "tr": lambda text, **values: translate(text, lang, **values),
                "translations": messages_for(lang),
                "amount": lambda value: format_amount(value, lang)}
