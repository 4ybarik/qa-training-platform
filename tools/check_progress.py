"""Трекер прогресса обучения: какие задачи каталога уже начаты.

Сканер читает таблицы AUTOMATION_PRACTICE_CATALOG.md и сверяет рекомендованные
файлы решений с тем, что реально существует в student_tests/. Никакой магии:
файл есть — задача считается начатой, файла нет — ждёт вас.

Запуск:
    python tools/check_progress.py
    make progress

Коды выхода: 0 — всегда (скрипт информационный), если не задан --strict
(тогда 1 при наличии хотя бы одной незавершённой задачи — удобно для CI).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG = REPO_ROOT / "AUTOMATION_PRACTICE_CATALOG.md"
STUDENT_DIR = REPO_ROOT / "student_tests"

ROW_RE = re.compile(
    r"^\|\s*([^|]+?)\s*\|[^|]+\|\s*`([^`]+)`\s*\|\s*(basic|intermediate|advanced)\s*\|$"
)
SECTION_RE = re.compile(r"^##\s+(.+)$")

LEVEL_LABEL = {"basic": "базовый", "intermediate": "средний", "advanced": "продвинутый"}
STATUS_DONE = "[x]"
STATUS_STARTED = "[~]"
STATUS_TODO = "[ ]"


def parse_catalog() -> list[dict[str, str]]:
    """Извлекает из каталога тройки (секция, файл решения, уровень)."""
    tasks: list[dict[str, str]] = []
    section = ""
    for line in CATALOG.read_text(encoding="utf-8").splitlines():
        if heading := SECTION_RE.match(line):
            section = heading.group(1).strip()
        if match := ROW_RE.match(line):
            tasks.append(
                {
                    "section": section,
                    "file": match.group(2),
                    "level": match.group(3),
                }
            )
    return tasks


def solution_exists(relative: str) -> bool:
    return (STUDENT_DIR / relative).is_file()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="вернуть код 1, если остались задачи без файла решения",
    )
    args = parser.parse_args()

    tasks = parse_catalog()
    if not tasks:
        print("Не удалось разобрать каталог задач:", CATALOG)
        return 1

    current_section = ""
    done = 0
    for task in tasks:
        exists = solution_exists(task["file"])
        done += exists
        mark = STATUS_DONE if exists else STATUS_TODO
        if task["section"] != current_section:
            current_section = task["section"]
            print(f"\n== {current_section} ==")
        state = "начата" if exists else "не начата"
        print(f"  {mark} {task['file']:<45} [{LEVEL_LABEL[task['level']]}] {state}")

    total = len(tasks)
    print(f"\nПрогресс: {done}/{total} задач имеют файл решения ({done * 100 // total}%).")

    started_files = sorted(
        {str(path.relative_to(STUDENT_DIR)) for path in STUDENT_DIR.rglob("test_*.py")}
    )
    catalog_files = {task["file"] for task in tasks}
    extra = [name for name in started_files if name not in catalog_files]
    if extra:
        print("\nВаши файлы вне рекомендованных имён каталога:")
        for name in extra:
            print(f"  {STATUS_STARTED} {name}")

    if args.strict and done < total:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
