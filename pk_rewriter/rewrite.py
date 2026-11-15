"""Rewrite Polish text into Polszczyzna Kontrolowana (PK) with a local model served by Ollama.

Loop: generate, check with pklint and the number check, repair. At most 3 model calls.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request

from . import pklint

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OPTIONS = {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "seed": 42, "num_ctx": 4096, "num_predict": 1024}
MAX_ROUNDS = 3
MARKER = "[DO USTALENIA"

SYSTEM = """Przepisz polski tekst na Polszczyznę Kontrolowaną (PK). Każde zdanie w PK ma dokładnie 1 znaczenie.

Zasady:
1. Nie zgaduj faktów. Jeżeli brakuje liczby, granicy, wykonawcy, obiektu lub daty, to wstaw znacznik [DO USTALENIA: czego brakuje].
2. Nie wybieraj znaczenia po cichu. Jeżeli zdanie ma 2 znaczenia, to wstaw znacznik.
3. Sprawdź wynik według każdej reguły.

Reguły:
- Zachowaj każdą liczbę z tekstu.
- Nadaj obiektowi nazwę, np. drukarka D1. Powtarzaj nazwę zamiast zaimka.
- Nazwij wykonawcę działania. Instrukcję pisz w trybie rozkazującym.
- Pisz wielkimi literami: MUSI, NIE WOLNO, POWINIEN, MOŻE.
- Warunek zapisz wzorem „Jeżeli W, to D.”.
- „Lub” znaczy co najmniej 1. „Albo” znaczy dokładnie 1. Nie łącz „i” z „lub” w 1 zdaniu.
- Granicę zapisz słowami „co najmniej N”, „co najwyżej N”, „więcej niż N”, „mniej niż N”, „od A do B włącznie”.
- Zdanie ma co najwyżej 20 słów i co najwyżej 1 słowo „nie”.
- Nie pisz: „należy”, „trzeba”, „jeśli”, „chyba że”, „bądź”, „itp.”, „około”, „kilka”, „regularnie”, „niezwłocznie”.
- Nie pisz: „odpowiedni”, „ostatni”, „następnie”, „jutro”, „powyżej”, „poniżej”, „między”, „w ciągu”, „musi”, „może”.

Odpowiedz tylko tekstem w PK. Nie dodawaj komentarza.

Przykład 1.
Tekst: Jeśli papier się zatnie, trzeba wyjąć go z drukarki.
PK: Gdy papier utknie w drukarce D1, wyjmij papier z drukarki D1.

Przykład 2.
Tekst: Administrator kasuje stare kopie bazy po 30 dniach, zwykle w nocy.
PK: Administrator usuwa każdą kopię bazy B1, która ma więcej niż 30 dni. Administrator usuwa kopię o godz. [DO USTALENIA: godzina]."""

# One sentence of SKILL.md (PK 0.1) per pklint code: a quotation, or a row of the table
# "Słowa zakazane" written as one sentence.
RULES = {
    "A2": "Dla obiektu bez nazwy podaj ilość: „każdy”, „dokładnie 1”, „co najmniej 1”.",
    "A3": "Powtórz nazwę obiektu.",
    "A4": "Zamiast słowa „ostatni” napisz „końcowy” albo nazwę z datą.",
    "A5": "Zastąp słowo nieostre liczbą z jednostką albo warunkiem, który czytelnik potrafi sprawdzić.",
    "A6": "Nie kończ wyliczenia słowami „itp.”, „itd.”, „i inne”.",
    "B1": "Nazwij wykonawcę w każdym zdaniu o działaniu.",
    "B5": "Nie używaj imiesłowów z końcówką „-ąc”, „-wszy”, „-łszy”.",
    "B8": "Opis ma co najwyżej 25 słów.",
    "C1": "Zamiast słów „bądź”, „względnie”, „ewentualnie”, „i/lub” napisz „lub” albo „albo”.",
    "C2": "Nie łącz słowa „i” ze słowem „lub” ani ze słowem „albo” w 1 zdaniu.",
    "C3": "Zamiast słów „jeśli”, „o ile”, „w razie”, „chyba że” użyj wzoru „Jeżeli W, to D.”.",
    "C4": "Nie łącz słów „wszyscy”, „wszystkie”, „każdy” z przeczeniem.",
    "C5": "Jedno zdanie zawiera co najwyżej 1 przeczenie.",
    "D1": "Oddziel części dziesiętne przecinkiem.",
    "D2": "Zapisz granicę słowami „co najmniej N”, „co najwyżej N”, „więcej niż N”, „mniej niż N” albo „od A do B włącznie”.",
    "D3": "Nie używaj słów, które zależą od dnia czytania: „dziś”, „jutro”, „w przyszłym tygodniu”.",
    "D4": "Dla terminu w dniach podaj 3 dane: zdarzenie początkowe, liczbę dni, dzień numer 1.",
    "D6": "Liczbę równą co najmniej 10^9 zapisz ze skrótem „mld” albo jako potęgę liczby 10.",
    "E4": "Odsyłaj do numeru lub do nazwy: „patrz krok 4”, „reguła C1”.",
    "F": "Nie używaj słów „podobno”, „chyba”, „raczej”, „prawdopodobnie”.",
    "KW": "Pisz wielkimi literami słowa kluczowe MUSI, NIE WOLNO, POWINIEN i MOŻE.",
}
WHAT = {code: what for code, _rule, what, _fn in pklint.CHECKS}
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def chat(model, messages):
    """One non-streaming call of Ollama /api/chat; returns the response as a dict."""
    body = {"model": model, "messages": messages, "stream": False, "think": False, "options": OPTIONS}
    req = urllib.request.Request(OLLAMA_URL + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp)


def numbers(text):
    """Numbers of a text; '2.5' equals '2,5' and '02' equals '2'."""
    return {re.sub(r"^0+(?=\d)", "", n.replace(".", ",")) for n in NUMBER.findall(text)}


def violations(text):
    """pklint hits as a list of {code, rule, what, sentence}; one item per code and sentence."""
    _hits, _words, _n, examples = pklint.lint(text)
    return [{"code": code, "rule": RULES[code], "what": WHAT[code], "sentence": s}
            for code in pklint.CODES for s in examples.get(code, [])]


def check(source, text):
    """Violations and the numbers of the source missing in the text; a marker excuses missing numbers."""
    missing = [] if MARKER in text else sorted(numbers(source) - numbers(text))
    return violations(text), missing


def repair_prompt(found, missing, empty):
    lines = ["Tekst w PK ma błędy. Popraw każdy błąd z listy:"]
    if empty:
        lines.append("- Odpowiedź jest pusta. Napisz tekst w PK.")
    for v in found:
        lines.append(f"- {v['code']}: {v['what']}. Zdanie: „{v['sentence']}”. Reguła: {v['rule']}")
    if missing:
        lines.append("- Brakuje liczb z tekstu źródłowego: " + "; ".join(missing)
                     + ". Zachowaj każdą liczbę z tekstu źródłowego.")
    lines.append("Odpowiedz tylko poprawionym tekstem w PK.")
    return "\n".join(lines)


def problems(rnd):
    return len(rnd["violations"]) + len(rnd["missing_numbers"]) + (0 if rnd["text"] else 1)


def rewrite(text, model, rounds=MAX_ROUNDS):
    """Generate, check, repair. Returns {text, ok, rounds, history}.

    text is the round with the fewest problems (the earliest on a tie); ok is True when that round
    has no pklint hit, no missing number and is not empty.
    """
    rounds = max(1, min(rounds, MAX_ROUNDS))
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}]
    history = []
    for _ in range(rounds):
        resp = chat(model, messages)
        out = resp.get("message", {}).get("content", "").strip()
        found, missing = check(text, out)
        history.append({"text": out, "violations": found, "missing_numbers": missing,
                        "prompt_eval_count": resp.get("prompt_eval_count", 0), "eval_count": resp.get("eval_count", 0),
                        "eval_seconds": resp.get("eval_duration", 0) / 1e9})
        if not problems(history[-1]):
            break
        messages = messages[:2] + [{"role": "assistant", "content": out},
                                   {"role": "user", "content": repair_prompt(found, missing, not out)}]
    best = min(history, key=problems)
    return {"text": best["text"], "ok": problems(best) == 0, "rounds": len(history), "history": history}
