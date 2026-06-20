# Архитектура QA Training Platform

Этот документ объясняет, как устроен проект, и пошагово показывает, как его
расширять: добавить таблицу в БД, новый эндпоинт, новую страницу, новый тест.
Структура документа: сначала — общая картина слоёв, затем — один сквозной
пример («Отзывы к курсу»), который проходит через все слои подряд, затем —
отдельные рецепты для типовых изменений, которые не требуют новой сущности.

---

## 1. Слои и поток запроса

```
HTTP-запрос
   |
   v
app/api/*.py  или  app/web/router.py     <- приём запроса, валидация входа (Pydantic/Form),
   |                                        проверка прав (RBAC), НИКАКОЙ бизнес-логики
   v
app/services/*.py                         <- бизнес-правила, транзакции (commit), audit log
   |
   v
app/repositories/*.py                     <- только запросы к БД (select/insert/update/delete),
   |                                        никакой бизнес-логики
   v
app/domain/models.py                      <- ORM-модели (структура таблиц)
   |
   v
PostgreSQL / SQLite
```

Правило простое: **каждый слой знает только о слое под собой**. API не лезет
в репозиторий напрямую — только через сервис. Репозиторий не содержит проверок
прав или бизнес-правил — только запросы. Если вы добавляете код и не уверены,
в какой слой его положить, — задайте себе вопрос:

- Это про HTTP (статусы, заголовки, парсинг формы)? -> `api/` или `web/`
- Это про правило/политику («нельзя удалить курс, если на него кто-то
  записан», «при создании курса логируем в audit»)? -> `services/`
- Это про SQL-запрос («найти курсы по категории», «посчитать количество
  записей»)? -> `repositories/`
- Это про форму данных (какие поля есть у курса)? -> `domain/models.py`
  (хранение) и `domain/schemas.py` (контракт API)

Дополнительно у проекта два параллельных входа в одну и ту же бизнес-логику:

- `app/api/*.py` — JSON REST API (используется автотестами, Swagger на `/docs`)
- `app/web/router.py` — серверные HTML-страницы (Jinja, для UI-автотестов)

Оба слоя вызывают **одни и те же сервисы** — бизнес-логика не дублируется.

---

## 2. Сквозной пример: добавляем сущность «Отзыв к курсу»

Сейчас на странице курса (`/courses/{id}`, вкладка «Отзывы») отзывы
захардкожены прямо в шаблоне. Сделаем их настоящей сущностью с таблицей,
API и формой добавления. Это покажет все слои на одном примере.

### Шаг 1 — модель (таблица в БД)

Открываем `backend/app/domain/models.py`, добавляем класс рядом с другими
моделями (стиль — `Mapped[...]` / `mapped_column` — везде одинаковый):

```python
class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..5
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    course: Mapped["Course"] = relationship(back_populates="reviews")
    user: Mapped["User"] = relationship()
```

И добавляем обратную связь в `Course`:

```python
class Course(Base):
    ...
    reviews: Mapped[list["Review"]] = relationship(back_populates="course", cascade="all, delete-orphan")
```

**Как таблица реально появляется в БД.** В этом проекте нет отдельного
механизма миграций (Alembic и т.п.) — это сознательное упрощение для учебного
полигона. Таблицы создаются функцией `init_db()` (`app/core/database.py`),
которая вызывает `Base.metadata.create_all(bind=engine)` при старте
приложения (см. `lifespan` в `app/main.py`). `create_all` создаёт **только
отсутствующие** таблицы — она не трогает существующие и не делает ALTER TABLE.

Значит, чтобы новая таблица `reviews` появилась:

- **Если у вас ещё нет данных, которыми дорожите** — самый простой путь:
  ```bash
  docker compose down -v   # удаляет volume с данными Postgres
  docker compose up -d --build
  ```
  При следующем старте `create_all` создаст все таблицы с нуля, включая новую.

- **Если нужно сохранить существующие данные** — добавьте таблицу вручную
  через SQL (выполнить один раз):
  ```bash
  docker compose exec db psql -U qatp -d qatp -c "
    CREATE TABLE reviews (
      id SERIAL PRIMARY KEY,
      course_id INTEGER NOT NULL REFERENCES courses(id),
      user_id INTEGER NOT NULL REFERENCES users(id),
      rating INTEGER NOT NULL,
      comment TEXT DEFAULT '',
      created_at TIMESTAMPTZ DEFAULT now()
    );
  "
  ```
  Колонки и типы должны соответствовать тому, что вы описали в `models.py`
  (`Integer` -> `INTEGER`, `String(N)` -> `VARCHAR(N)`, `Text` -> `TEXT`,
  `DateTime(timezone=True)` -> `TIMESTAMPTZ`, `Boolean` -> `BOOLEAN`).

- **Если проект вырастет за пределы учебного** — стоит подключить Alembic
  (`pip install alembic`, `alembic init migrations`) для версионируемых
  миграций. Это осознанно не сделано здесь, чтобы не усложнять старт.

### Шаг 2 — схема (контракт API)

`backend/app/domain/schemas.py` — добавляем рядом с другими `*Out`/`*Create`:

```python
class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    rating: int
    comment: str
    created_at: datetime


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)
```

### Шаг 3 — репозиторий (запросы к БД)

`backend/app/repositories/courses.py` — добавляем новый класс рядом
с `CourseRepository`/`EnrollmentRepository`:

```python
class ReviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_course(self, course_id: int) -> list[Review]:
        return list(
            self.db.scalars(
                select(Review).where(Review.course_id == course_id)
                .order_by(Review.created_at.desc())
            )
        )

    def add(self, review: Review) -> Review:
        self.db.add(review)
        self.db.flush()
        return review
```

(не забудьте `from app.domain.models import Review` в импортах файла)

### Шаг 4 — сервис (бизнес-правило)

`backend/app/services/courses.py` — добавляем метод в `CourseService`
(или отдельный `ReviewService`, если логика разрастётся):

```python
def add_review(self, user_id: int, course_id: int, data: ReviewCreate) -> Review:
    course = self.get(course_id)  # бросит NotFoundError, если курса нет
    review = Review(course_id=course_id, user_id=user_id, rating=data.rating, comment=data.comment)
    self.reviews.add(review)
    self.db.add(AuditLog(user_id=user_id, action="review_added", payload=str(course_id)))
    self.db.commit()
    self.db.refresh(review)
    return review
```

Здесь видно правило слоёв на практике: сервис **сначала** проверяет, что курс
существует (используя уже готовый `self.get()`), **затем** делает запись и
**сам** управляет транзакцией (`commit`). Репозиторий ничего не знает о том,
что нужно проверить существование курса или записать в audit log — это
бизнес-правило, не запрос к БД.

### Шаг 5 — API-эндпоинт

`backend/app/api/courses.py`:

```python
@router.get("/{course_id}/reviews", response_model=list[ReviewOut])
def list_reviews(course_id: int, db: Session = Depends(get_db)):
    return CourseService(db).reviews.list_for_course(course_id)


@router.post("/{course_id}/reviews", response_model=ReviewOut, status_code=201)
def add_review(course_id: int, payload: ReviewCreate,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CourseService(db).add_review(user.id, course_id, payload)
```

Заметьте: здесь **не** используется `require_roles(Role.ADMIN)` — отзывы
оставляют обычные пользователи, не только администраторы. Если бы нужно было
ограничить действие только ADMIN (как с курсами/экзаменами), мы бы заменили
`Depends(get_current_user)` на `Depends(require_roles(Role.ADMIN))` — это
единственное, что нужно поменять для RBAC (см. раздел 4 ниже).

### Шаг 6 — веб-страница (опционально)

Если нужна форма добавления отзыва в `course_detail.html`, добавляем в
`web/router.py`:

```python
@router.post("/web/courses/{course_id}/reviews")
def review_submit(course_id: int, rating: int = Form(...), comment: str = Form(""),
                  user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if (r := _require_web_user(user)):
        return r
    CourseService(db).add_review(user.id, course_id, ReviewCreate(rating=rating, comment=comment))
    return RedirectResponse(f"/courses/{course_id}", status_code=303)
```

И в `course_detail.html`, в блоке `tab-reviews-panel`, заменяем захардкоженные
`<div class="review">` на цикл `{% for review in reviews %}` (передав `reviews`
из роутера через `_ctx(..., reviews=CourseService(db).reviews.list_for_course(course_id))`)
плюс форму с `data-testid="review-form"` для автотестов.

### Шаг 7 — тест

`backend/tests/test_courses_api.py`:

```python
def test_add_and_list_review(client, user_token):
    r = client.post("/api/courses/1/reviews", headers=auth(user_token),
                    json={"rating": 5, "comment": "Отличный курс"})
    assert r.status_code == 201
    assert r.json()["rating"] == 5

    listing = client.get("/api/courses/1/reviews")
    assert listing.status_code == 200
    assert any(rv["comment"] == "Отличный курс" for rv in listing.json())
```

Это и есть полный цикл: **модель -> схема -> репозиторий -> сервис -> API ->
шаблон -> тест**. Любая новая сущность в проекте (например, «Сертификаты»,
«Тарифы», «Группы пользователей») добавляется по этому же шаблону.

---

## 3. Рецепт: добавить поле к существующей сущности

Более частый случай, чем новая таблица. Пример: добавить полю `Course`
поле `duration_hours` (длительность курса в часах).

1. **Модель** (`domain/models.py`): добавить
   `duration_hours: Mapped[int] = mapped_column(Integer, default=0)` в класс `Course`.
2. **БД**: т.к. таблица уже существует, `create_all()` новую колонку не
   добавит (он не делает ALTER TABLE). Нужно либо пересоздать БД
   (`docker compose down -v && docker compose up -d --build` — теряются данные),
   либо выполнить вручную:
   ```bash
   docker compose exec db psql -U qatp -d qatp -c "ALTER TABLE courses ADD COLUMN duration_hours INTEGER DEFAULT 0;"
   ```
3. **Схема** (`domain/schemas.py`): добавить поле в `CourseOut`, `CourseCreate`,
   `CourseUpdate` — три места, по аналогии с уже существующими полями (`price`,
   `category`).
4. **Сервис**: если это не просто поле для отображения, а логика на нём
   завязана — учесть в `CourseService.create`/`update`. Если поле проходит
   «как есть» через `CourseCreate`/`CourseUpdate` (как сейчас `price`), то
   ничего менять не нужно — `model_dump(exclude_unset=True)` в `update()`
   подхватит новое поле автоматически.
5. **Шаблоны**: добавить `<input>` в `course_form.html`, вывод — в
   `course_detail.html`/`courses.html`, если нужно показывать в списке.

---

## 4. Рецепт: ограничить эндпоинт ролью (RBAC)

Вся ролевая модель опирается на одну фабрику зависимостей —
`require_roles()` в `app/api/deps.py`:

```python
def require_roles(*roles: Role):
    allowed = set(roles)
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="Недостаточно прав...")
        return user
    return checker
```

Чтобы ограничить **API**-эндпоинт только ADMIN, замените зависимость:

```python
# было — доступно любому авторизованному:
def my_endpoint(user: User = Depends(get_current_user)): ...

# стало — доступно только ADMIN:
def my_endpoint(user: User = Depends(require_roles(Role.ADMIN))): ...
```

Можно перечислить несколько ролей: `require_roles(Role.ADMIN, Role.MANAGER)`.

Чтобы ограничить **веб-страницу**, используйте готовый helper `_require_admin`
из `web/router.py` (он же отдаёт `forbidden.html` со статусом 403 для
GET-страниц) или ручную проверку `if user.role != Role.ADMIN: return RedirectResponse(...)`
для POST-обработчиков форм (см. `course_delete_submit` как пример).

**Важно про порядок проверок**: всегда сначала проверяйте права, затем
существование ресурса — это явно видно в `exam_delete_submit`
(`web/router.py`): сначала `if user is None`, затем загрузка объекта,
затем `if user.role != Role.ADMIN`. Обратный порядок (искать объект раньше
прав) — менее эффективен (лишний запрос к БД для запросов без доступа), хотя
функционально оба варианта дают верный итоговый ответ.

---

## 5. Рецепт: добавить новый сервис тестов / автоматизации

Если в проект нужно добавить ещё один вид тестов (например, нагрузочные
тесты на Locust, контрактные тесты на Pact):

1. Создайте директорию на уровне `backend/`/`e2e/` — например, `load/`.
2. Добавьте `requirements.txt` со своими зависимостями (по аналогии с `e2e/requirements.txt`).
3. Для интеграции с Allure добавьте `allure-pytest` (если фреймворк на pytest)
   или нативный Allure-адаптер для другого раннера, и пишите результаты в
   `--alluredir=../allure-results/<имя-сервиса>` — Allure-сервис из
   `docker-compose.yml` подхватывает **все** поддиректории `allure-results/`.
4. Добавьте новую стадию в `Jenkinsfile` по образцу существующих стадий
   `API tests` / `E2E tests`.

---

## 6. Рецепт: добавить новый внешний сервис (Redis, Kafka, и т.п.)

Текущая архитектура спроектирована так, чтобы такие сервисы добавлялись
точечно, не трогая бизнес-логику:

- **Redis** (замена in-memory rate limiter/кэша): реализация спрятана за
  интерфейсом `RateLimiter` (`app/core/rate_limit.py`). Чтобы переключиться
  на Redis, создайте `RedisRateLimiter` с тем же публичным интерфейсом
  (`hit(key) -> bool`, `reset(key) -> None`) и замените инстанциирование в
  `app/services/auth.py` (`login_limiter = RateLimiter(...)` ->
  `RedisRateLimiter(...)`). Остальной код не меняется. Добавьте сервис
  `redis` в `docker-compose.yml` по аналогии с `db`.
- **Kafka**: точки эмиссии доменных событий уже локализованы в сервисах —
  везде, где сейчас пишется `AuditLog`/`Notification` (например,
  `CourseService.enroll`, `ExamService.submit`), это естественное место
  для `producer.send("course.enrolled", ...)`. Добавьте Kafka-клиент
  (`pip install confluent-kafka` или `aiokafka`) и сервис `kafka`+`zookeeper`
  в `docker-compose.yml`.
- **Разделение на микросервисы**: модули `services/*.py` и `api/*.py` уже
  сгруппированы по доменам (`auth`, `courses`, `exams`, `admin`) — каждый
  такой модуль можно вынести в отдельный FastAPI-проект с собственной БД,
  заменив прямые вызовы сервисов на HTTP/gRPC-вызовы между сервисами.

---

## 7. Где что лежит — краткий указатель

| Хочу изменить...                            | Файл(ы)                                                       |
|----------------------------------------------|-----------------------------------------------------------------|
| Структуру таблицы / новую таблицу            | `backend/app/domain/models.py`                                  |
| Формат запроса/ответа API                    | `backend/app/domain/schemas.py`                                 |
| SQL-запрос (поиск, фильтр, сортировка)       | `backend/app/repositories/*.py`                                 |
| Бизнес-правило (валидация, побочные эффекты) | `backend/app/services/*.py`                                     |
| JSON API-эндпоинт                            | `backend/app/api/*.py`                                          |
| HTML-страницу/форму                          | `backend/app/web/router.py` + `backend/app/templates/*.html`    |
| Стили                                        | `backend/app/static/css/app.css`                                |
| Клиентскую интерактивность (модалки, DnD)    | `backend/app/static/js/app.js`                                  |
| RBAC-проверку                                | `backend/app/api/deps.py` (`require_roles`)                     |
| Демо-данные                                  | `backend/app/seed.py`                                           |
| Настройки приложения (env-переменные)        | `backend/app/core/config.py`                                    |
| API-тест                                     | `backend/tests/test_*.py`                                       |
| E2E-тест (Playwright)                        | `e2e/test_*.py`                                                 |
| CI-пайплайн                                  | `Jenkinsfile`                                                   |
| Состав контейнеров                           | `docker-compose.yml`                                            |
