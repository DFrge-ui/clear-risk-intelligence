"""Shared source-string translations for Jinja, browser UI and report prose."""
import json
from functools import lru_cache
from pathlib import Path

from flask import request


@lru_cache(maxsize=1)
def russian_messages():
    return json.loads((Path(__file__).parent / "locales" / "ru.json").read_text(encoding="utf-8"))


def language():
    value = request.args.get("lang", request.cookies.get("clear_language", "en"))
    return "ru" if value == "ru" else "en"


def translate(message, lang=None, **values):
    lang = lang or language()
    translated = russian_messages().get(message, message) if lang == "ru" else message
    for key, value in values.items():
        translated = translated.replace("{" + key + "}", str(value))
    return translated


def localize_summary(summary, as_of, lang):
    """Translate prose from already computed facts; do not recalculate any metric."""
    if lang != "ru":
        return summary
    result = summary.copy()
    m = summary["metrics"]
    if not m["total"]:
        result["narrative"] = translate("No incidents match these filters. Broaden the selection to generate a management summary.", lang)
        return result
    top = summary["categories"][0]
    money = lambda value: f"{value:,.2f}".replace(",", " ").replace(".", ",")
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
                "translations": russian_messages() if lang == "ru" else {},
                "amount": lambda value: f"{value:,.2f}".replace(",", " ").replace(".", ",") if lang == "ru" else f"{value:,.2f}"}
