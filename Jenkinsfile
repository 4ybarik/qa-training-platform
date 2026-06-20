// Jenkinsfile — пайплайн CI для QA Training Platform.
//
// ВАЖНО: этот Jenkinsfile — рабочая отправная точка, а не «прогнанный на проде»
// готовый пайплайн. Реальные Jenkins-окружения отличаются версией Docker,
// установленными плагинами и сетевыми настройками, поэтому перед первым
// запуском проверьте: 1) у пользователя Jenkins есть доступ к docker.sock
// (см. volume в docker-compose.yml), 2) сетевое имя "qatp_ci_default" в стадии
// E2E соответствует реально созданной docker compose сетью (проверьте через
// `docker network ls` после первого `docker compose up`), 3) шаг allure() в
// post{} закомментирован по умолчанию — Allure Jenkins Plugin у некоторых
// версий Jenkins ставится нестабильно; раскомментируйте строку в post{},
// когда плагин установится без ошибок. До этого отчёты доступны через
// отдельный контейнер allure на http://localhost:5050 — без участия плагина.
//
// Эту джобу нужно создавать как Pipeline с типом "Pipeline script" (текст
// Jenkinsfile вставляется прямо в поле Script), а НЕ "Pipeline script from
// SCM" — последний требует настроенный источник (Git и т.п.) и без него
// падает с ошибкой "Jenkinsfile not found".
//
// Про Docker-outside-of-Docker и пути для volumes: Jenkins запускает ДОЧЕРНИЕ
// контейнеры (для тестов) через проброшенный docker.sock хоста, а не через
// собственный Docker-движок. Это значит, что любой volume-маунт для дочернего
// контейнера должен указывать РЕАЛЬНЫЙ путь на хосте, а не путь, видимый
// изнутри самого Jenkins-контейнера ("/workspace" — это путь только для
// Jenkins, демон Docker хоста его не знает). Поэтому используется переменная
// окружения HOST_PROJECT_DIR (см. docker-compose.yml, сервис jenkins,
// environment.HOST_PROJECT_DIR = "${PWD}") — она прокинута в контейнер
// Jenkins при его собственном старте и содержит реальный путь на хосте.
//
// Про Allure-результаты: контейнер allure (см. docker-compose.yml) слушает
// ИМЕНОВАННЫЙ Docker volume "allure_results" — а не путь на файловой системе.
// Имя volume, которое реально создаёт Compose, формируется как
// "<имя_проекта>_allure_results", где имя проекта — это имя директории
// репозитория по умолчанию (для обычного `docker compose up`, без -p).
// Стадии тестов ниже подключаются к ЭТОМУ ЖЕ volume по полному имени —
// специально, а не к изолированному volume CI-проекта qatp_ci, потому что
// allure-сервис один на весь хост и должен видеть результаты любых прогонов.
// Если вы переименуете директорию репозитория, обновите ALLURE_VOLUME ниже.
//
// Про порты: docker-compose.yml сам по себе НЕ пробрасывает порты db/app на
// хост — это сделано в docker-compose.override.yml, который Docker Compose
// подключает АВТОМАТИЧЕСКИ только при отсутствии явного -f (то есть при
// обычном `docker compose up` для разработки). Команды в этом Jenkinsfile
// используют явный `-f docker-compose.yml` — из-за этого override НЕ
// подключается, и CI-копия стека (другое имя проекта — qatp_ci) поднимается
// без портов на хост, не конкурируя с уже запущенным локально основным
// стеком за порты 5432/8000 ("port is already allocated" больше не возникает).
// Тестам проброс портов не нужен — все обращения идут по внутренним DNS-именам
// docker-сети (db:5432, app:8000), без выхода на localhost хоста.
//
// Что делает пайплайн:
//   1. Checkout кода (Jenkins уже видит репозиторий через volume ./:/workspace,
//      поэтому здесь просто используется рабочая директория).
//   2. Поднимает app + db через docker compose (полный стек проекта, без
//      проброса портов наружу — см. примечание про порты выше).
//   3. Прогоняет API-тесты (pytest) внутри контейнера app.
//   4. Прогоняет E2E-тесты (Playwright) через временный контейнер с готовым
//      образом Playwright (без отдельного Jenkins-плагина).
//   5. Собирает allure-результаты в общую папку allure-results/, откуда их
//      забирает контейнер allure (см. docker-compose.yml) и автоматически
//      рендерит HTML-отчёт на http://localhost:5050.
//   6. Публикация отчёта прямо во вкладке сборки Jenkins (через шаг allure())
//      закомментирована по умолчанию — включите её, когда поставите плагин
//      Allure Jenkins Plugin без ошибок (см. пункт 3 выше).

pipeline {
    agent any

    environment {
        COMPOSE_PROJECT_NAME = "qatp_ci"
        ALLURE_RESULTS_DIR = "allure-results"
        // Полное имя volume основного проекта (см. блок комментариев выше про
        // Allure-результаты). "qa-training-platform" — это имя директории
        // репозитория, под которым Compose назвал volume при обычном
        // `docker compose up` (project name по умолчанию = имя директории).
        ALLURE_VOLUME = "qa-training-platform_allure_results"
        // Явный -f — гарантирует, что docker-compose.override.yml (с портами
        // для разработки) НЕ подключится автоматически. Без явного -f Compose
        // сам бы подмешал override и порты снова бы конфликтовали с хостом.
        COMPOSE = "docker compose -f docker-compose.yml"
    }

    stages {
        stage('Build') {
            steps {
                dir('/workspace') {
                    // APP_VERSION подставляется из Git так же, как при локальной
                    // сборке через `make up` — единый источник правды (см. config.py).
                    // git config safe.directory нужен, потому что /workspace смонтирован
                    // как volume с хоста — Git защищается от такого сценария по
                    // умолчанию ("detected dubious ownership"), это снимает защиту
                    // для этой конкретной директории.
                    sh '''
                        git config --global --add safe.directory /workspace
                        export APP_VERSION=$(git describe --tags --always --dirty 2>/dev/null || echo 0.0.0-dev)
                        echo "Собираем версию: ${APP_VERSION}"
                        ${COMPOSE} build app
                    '''
                }
            }
        }

        stage('Up (app + db)') {
            steps {
                dir('/workspace') {
                    sh '${COMPOSE} up -d db app'
                    // Порты наружу не пробрасываются (override.yml не подключён
                    // из-за явного -f выше), поэтому проверяем готовность app
                    // изнутри той же docker-сети, по имени "app:8000", а не localhost.
                    sh '''
                        for i in $(seq 1 30); do
                          if docker run --rm --network ${COMPOSE_PROJECT_NAME}_default curlimages/curl:latest \
                             -sf http://app:8000/health > /dev/null 2>&1; then
                            echo "app готов"; exit 0
                          fi
                          sleep 2
                        done
                        echo "app не поднялся за отведённое время"
                        ${COMPOSE} logs app
                        exit 1
                    '''
                }
            }
        }

        stage('API tests (pytest)') {
            steps {
                dir('/workspace') {
                    // Выполняем тесты внутри уже собранного образа app — там есть
                    // весь Python-стек проекта. Сам контейнер app продолжает работать
                    // отдельно (это разовый одноразовый контейнер для прогона тестов).
                    //
                    // ВАЖНО: пишем результаты в ИМЕНОВАННЫЙ Docker volume
                    // ALLURE_VOLUME (полное имя — см. environment{} выше), а НЕ на
                    // путь файловой системы хоста. Контейнер allure (docker-compose.yml)
                    // слушает именно этот volume, а не произвольную папку на диске —
                    // см. подробное объяснение в комментариях в начале файла, блок
                    // "Про Allure-результаты". Пишем в КОРЕНЬ volume (без подпапки
                    // /api), плоско вместе с результатами E2E ниже — allure-docker-service
                    // объединяет все файлы результатов из одной директории в общий отчёт;
                    // вложенные поддиректории он не гарантированно сканирует.
                    sh '''
                        ${COMPOSE} run --rm \
                          -v "${ALLURE_VOLUME}:/app/allure-results" \
                          --entrypoint sh app -c \
                          "pip install allure-pytest --break-system-packages --quiet && \
                           python -m pytest --alluredir=/app/allure-results"
                    '''
                }
            }
        }

        stage('E2E tests (Playwright)') {
            steps {
                dir('/workspace') {
                    // Вместо agent { docker {...} } (требует отдельный плагин
                    // "Docker Pipeline", который может быть не установлен)
                    // запускаем официальный образ Playwright вручную через
                    // docker run — это работает на голом agent any, нужен
                    // только docker.sock, который и так используется выше.
                    //
                    // Маунт исходного кода e2e/ — это путь на хосте (нужны
                    // реальные файлы тестов), используем $HOST_PROJECT_DIR вместо
                    // $(pwd) по той же причине, что и в стадии API tests выше
                    // (Docker-outside-of-Docker: путь для volumes должен быть
                    // путём на хосте, не внутри Jenkins-контейнера).
                    //
                    // Маунт результатов Allure — это ИМЕНОВАННЫЙ Docker volume
                    // (ALLURE_VOLUME), не путь на диске — см. блок комментариев
                    // про Allure-результаты в начале файла. Пишем в КОРЕНЬ volume,
                    // плоско вместе с результатами API-тестов (та же логика, что
                    // и в стадии API tests выше) — так не нужно полагаться на то,
                    // сканирует ли конкретная версия allure-docker-service
                    // вложенные поддиректории рекурсивно.
                    sh '''
                        docker run --rm \
                          --network ${COMPOSE_PROJECT_NAME}_default \
                          -v "${HOST_PROJECT_DIR}/e2e:/e2e" \
                          -v "${ALLURE_VOLUME}:/allure-results" \
                          -w /e2e \
                          -e BASE_URL=http://app:8000 \
                          mcr.microsoft.com/playwright/python:v1.45.0-jammy \
                          sh -c "pip install -r requirements.txt --quiet && \
                                 python -m pytest --alluredir=/allure-results"
                    '''
                }
            }
        }
    }

    post {
        always {
            // Шаг allure() закомментирован: плагин Allure Jenkins Plugin может
            // ставиться нестабильно в некоторых версиях Jenkins (известная
            // ReactorException/InvocationTargetException при установке).
            // Отчёты всё равно доступны без этого шага — через отдельный
            // контейнер allure из docker-compose.yml на http://localhost:5050,
            // он подхватывает файлы из volume allure_results автоматически
            // (см. ALLURE_VOLUME выше и блок комментариев про Allure-результаты
            // в начале файла).
            //
            // ВАЖНО, если решите включить плагин: он сканирует файлы НА ДИСКЕ
            // внутри самого контейнера Jenkins (а не Docker volume — плагин
            // работает изнутри Jenkins-процесса, не через docker run). Сейчас
            // стадии тестов пишут результаты прямо в Docker volume, минуя
            // файловую систему Jenkins, поэтому простого пути для плагина нет
            // "из коробки". Чтобы включить публикацию через плагин, сначала
            // скопируйте результаты из volume на диск Jenkins, например:
            //   docker run --rm -v ${ALLURE_VOLUME}:/src -v ${HOST_PROJECT_DIR}/${ALLURE_RESULTS_DIR}:/dst alpine cp -r /src/. /dst/
            // и только потом раскомментируйте строку ниже:
            // allure includeProperties: false, results: [[path: "${ALLURE_RESULTS_DIR}"]]

            dir('/workspace') {
                sh '${COMPOSE} down'
            }
        }
    }
}
