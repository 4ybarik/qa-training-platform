# Кастомный образ Jenkins с предустановленным Docker CLI.
#
# Базовый образ jenkins/jenkins не содержит клиента docker — только Java и
# сам Jenkins. Доступ к docker.sock хоста даёт КАНАЛ к демону Docker, но без
# самого CLI внутри контейнера команда `docker` не существует физически
# ("docker: not found" в выводе пайплайна). Этот Dockerfile решает именно
# это: добавляет docker-ce-cli и compose plugin поверх официального образа.
FROM jenkins/jenkins:lts-jdk21

USER root

# Устанавливаем Docker CLI (не демон — демон остаётся на хосте, мы только
# подключаемся к его сокету), docker compose plugin по официальной инструкции
# Docker для Debian/Ubuntu-подобных систем, и git (нужен для `git describe`
# в стадии Build — это источник версии приложения, см. APP_VERSION в Jenkinsfile).
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl gnupg git && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin && \
    rm -rf /var/lib/apt/lists/*

# Пользователь jenkins должен входить в группу docker, чтобы иметь права
# на сокет /var/run/docker.sock (он создаётся снаружи с GID хостовой группы
# docker; добавление группы here просто гарантирует, что она существует —
# реальный доступ даёт совпадение GID, см. примечание в docker-compose.yml).
RUN groupadd -f docker && usermod -aG docker jenkins

USER jenkins
