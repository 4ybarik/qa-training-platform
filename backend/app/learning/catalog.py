"""Связывает существующий каталог мишеней с короткими учебными уроками.

Каталог практики остаётся единственным источником правды для пути решения,
мишени и критериев. Теоретические фрагменты переиспользуются из seed-контента,
поэтому урок не расходится с уже опубликованными материалами.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
import re

from markupsafe import Markup

from app.practice.catalog import CHALLENGES, Challenge
from app.seed_content import COURSE_DESCRIPTIONS


THEORY_TRACKS: dict[str, tuple[str, ...]] = {
    "api-contracts": ("basics", "pytest", "http_api", "api_practice"),
    "security": ("security_rbac", "http_api"),
    "ui": ("playwright", "ui_practice"),
    "integration": ("data_integrations", "api_practice"),
    "reliability": ("contracts_reliability", "pytest"),
    "business-flows": ("ui_practice", "api_practice", "security_rbac"),
    "engineering-gates": ("cicd_reporting", "contracts_reliability", "data_integrations"),
}

MUTATIONS_BY_CHALLENGE: dict[str, tuple[str, ...]] = {
    "schema-variants": ("schema-wrong-type",),
    "resource-crud": ("resource-delete-noop",),
    "pagination-sort-search": ("pagination-ignore-size", "practice-list-phantom"),
    "idempotency-etag": ("etag-ignore-if-match",),
    "deterministic-rate-limit": ("rate-limit-disabled",),
    "login-ui": ("login-redirect",),
    "async-job": ("job-never-completes",),
    "file-roundtrip": ("file-content-corrupted",),
    "webhook-recorder": ("webhook-sequence-duplicate",),
    "localization-flow": ("language-noop",),
}


@dataclass(frozen=True)
class Lesson:
    slug: str
    track: str
    difficulty: str
    title: str
    task: str
    target: str
    test_path: str
    criteria: tuple[str, ...]
    markers: tuple[str, ...]
    theory_title: str
    theory_markdown: str
    theory_minutes: int
    practice_minutes: int
    starter_code: str | None
    mutation_ids: tuple[str, ...]

    @property
    def editable_path(self) -> str | None:
        prefix = "student_tests/"
        if self.starter_code is None or not self.test_path.startswith(prefix):
            return None
        return self.test_path.removeprefix(prefix)


def _theory_entries(track_slug: str) -> list[dict]:
    entries: list[dict] = []
    for theory_track in THEORY_TRACKS.get(track_slug, ("basics",)):
        entries.extend(COURSE_DESCRIPTIONS[theory_track])
    return entries


def _folder_marker(test_path: str) -> str:
    for marker in ("ui", "contract", "integration", "api"):
        if f"/{marker}/" in test_path:
            return marker
    return "reliability"


def _starter_code(challenge: Challenge, language: str) -> str | None:
    if not challenge.test_path.startswith("student_tests/") or not challenge.test_path.endswith(".py"):
        return None
    marker = _folder_marker(challenge.test_path)
    function_name = re.sub(r"[^a-z0-9_]+", "_", challenge.slug.lower()).strip("_")
    title = challenge.title.in_language(language)
    target = challenge.target
    if marker == "ui":
        return (
            f'"""{title}.\n\nМишень: {target}\n"""\n'
            "import pytest\n\n\n"
            "@pytest.mark.ui\n"
            f"def test_{function_name}(page, base_url):\n"
            "    # Arrange: откройте нужную страницу и подготовьте состояние.\n"
            "    # Act: выполните пользовательское действие через устойчивый локатор.\n"
            "    # Assert: проверьте наблюдаемое поведение, а не детали реализации.\n"
            '    pytest.fail("TODO: реализуйте критерии задачи")\n'
        )
    return (
        f'"""{title}.\n\nМишень: {target}\n"""\n'
        "import pytest\n\n\n"
        f"@pytest.mark.{marker}\n"
        f"def test_{function_name}(api_client):\n"
        "    # Arrange: подготовьте уникальные данные, если они нужны.\n"
        "    # Act: вызовите тестируемую мишень через api_client.\n"
        "    # Assert: проверьте статус, контракт и значимое поведение.\n"
        '    pytest.fail("TODO: реализуйте критерии задачи")\n'
    )


def lesson_for(challenge: Challenge, language: str = "ru") -> Lesson:
    siblings = [item for item in CHALLENGES if item.track == challenge.track]
    position = siblings.index(challenge)
    theory = _theory_entries(challenge.track)
    source = theory[position % len(theory)]
    theory_text = source["description"]
    if language == "en":
        theory_text = (
            f"{challenge.task.en}\n\n"
            "Use the target and acceptance criteria below as the executable contract. "
            "The detailed reference material is currently available in Russian."
        )
    return Lesson(
        slug=challenge.slug,
        track=challenge.track,
        difficulty=challenge.difficulty,
        title=challenge.title.in_language(language),
        task=challenge.task.in_language(language),
        target=challenge.target,
        test_path=challenge.test_path,
        criteria=tuple(item.in_language(language) for item in challenge.criteria),
        markers=challenge.markers,
        theory_title=source["title"],
        theory_markdown=theory_text,
        theory_minutes=5,
        practice_minutes=95,
        starter_code=_starter_code(challenge, language),
        mutation_ids=MUTATIONS_BY_CHALLENGE.get(challenge.slug, ()),
    )


def lessons(language: str = "ru") -> list[Lesson]:
    return [lesson_for(challenge, language) for challenge in CHALLENGES]


def _inline(text: str) -> str:
    safe = escape(text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)


def render_micro_markdown(value: str) -> Markup:
    """Рендерит доверенный учебный Markdown без разрешения произвольного HTML."""
    blocks: list[str] = []
    paragraph: list[str] = []
    code: list[str] = []
    code_language = ""
    in_code = False

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    for raw_line in value.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                blocks.append(
                    f'<pre><code class="language-{escape(code_language)}">'
                    f"{escape(chr(10).join(code))}</code></pre>"
                )
                code.clear()
                in_code = False
            else:
                flush_paragraph()
                code_language = line[3:].strip()
                in_code = True
            continue
        if in_code:
            code.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            continue
        if line.startswith("- "):
            flush_paragraph()
            blocks.append(f"<p>• {_inline(line[2:])}</p>")
            continue
        paragraph.append(line.strip())
    flush_paragraph()
    if in_code:
        blocks.append(f"<pre><code>{escape(chr(10).join(code))}</code></pre>")
    return Markup("\n".join(blocks))


def serialize_lesson(lesson: Lesson) -> dict:
    return {
        "slug": lesson.slug,
        "track": lesson.track,
        "difficulty": lesson.difficulty,
        "title": lesson.title,
        "task": lesson.task,
        "target": lesson.target,
        "test_path": lesson.test_path,
        "editable_path": lesson.editable_path,
        "criteria": list(lesson.criteria),
        "markers": list(lesson.markers),
        "theory_title": lesson.theory_title,
        "theory_markdown": lesson.theory_markdown,
        "theory_html": str(render_micro_markdown(lesson.theory_markdown)),
        "theory_minutes": lesson.theory_minutes,
        "practice_minutes": lesson.practice_minutes,
        "mutation_ids": list(lesson.mutation_ids),
    }
