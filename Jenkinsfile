// CI/CD pipeline: Git -> isolated Docker Compose stack -> tests -> reports.
//
// The job is intended to be configured as "Pipeline script from SCM" with this
// repository as its SCM source. A polling trigger is included as a portable
// fallback; a Git provider webhook can be used instead for faster feedback.
// Jenkins uses Docker-outside-of-Docker, therefore HOST_PROJECT_DIR must be the
// real host path (docker-compose.yml supplies it when the Jenkins container is
// started). The compose project name is unique per build, so PostgreSQL,
// Redis, RQ and WireMock are isolated from other builds.

pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '20'))
        timeout(time: 60, unit: 'MINUTES')
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    parameters {
        booleanParam(
            name: 'RUN_MUTATIONS',
            defaultValue: true,
            description: 'Запустить контролируемые мутации и проверить mutation score'
        )
        booleanParam(
            name: 'RUN_PERFORMANCE',
            defaultValue: true,
            description: 'Запустить короткий Locust smoke с порогом p95'
        )
    }

    environment {
        // BUILD_NUMBER делает Compose project name уникальным для каждой сборки.
        COMPOSE_PROJECT_NAME = "qatp_ci_${BUILD_NUMBER}"
        COMPOSE = "docker compose -p qatp_ci_${BUILD_NUMBER} -f docker-compose.yml"
        ALLURE_VOLUME = 'qa-training-platform_allure_results'
        ALLURE_RESULTS_DIR = 'allure-results'
        TEST_SUPPORT_KEY = 'ci-test-support-key'
        ALLOW_TEST_MUTATIONS = 'true'
        PERF_P95_LIMIT_MS = '750'
        PERF_FAILURE_RATIO = '0.01'
        PERF_MIN_REQUESTS = '20'
    }

    stages {
        stage('Checkout') {
            steps {
                dir('/workspace') {
                    script {
                        // The preferred mode is Pipeline script from SCM. The
                        // local training job may still be an inline Pipeline,
                        // where Jenkins exposes no `scm` object; in that mode
                        // use the repository mounted by docker-compose. Never
                        // hide a checkout failure when neither source exists.
                        try {
                            checkout scm
                        } catch (Exception checkoutError) {
                            if (sh(script: 'test -d .git', returnStatus: true) != 0) {
                                throw checkoutError
                            }
                            echo 'SCM checkout is unavailable for inline job; using mounted /workspace repository'
                        }
                        env.APP_VERSION = sh(
                            script: "git describe --tags --always --dirty 2>/dev/null || echo 0.0.0-dev",
                            returnStdout: true
                        ).trim()
                        env.CI_STARTED_AT = sh(script: 'date +%s', returnStdout: true).trim()
                    }
                    sh '''
                        git config --global --add safe.directory /workspace
                        mkdir -p ci-artifacts allure-results e2e/test-results student_tests/test-results
                        find ci-artifacts -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
                        find allure-results -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
                        find e2e/test-results -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
                        find student_tests/test-results -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
                        docker run --rm -v "${ALLURE_VOLUME}:/results" alpine:3.20 \
                          sh -c 'find /results -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +'
                        echo "commit=$(git rev-parse HEAD) version=${APP_VERSION} project=${COMPOSE_PROJECT_NAME}"
                    '''
                }
            }
        }

        stage('Build application') {
            steps {
                dir('/workspace') {
                    sh '''
                        export APP_VERSION="${APP_VERSION}"
                        ${COMPOSE} build app worker
                    '''
                }
            }
        }

        stage('Start isolated stack') {
            steps {
                dir('/workspace') {
                    sh '''
                        ${COMPOSE} up -d db redis wiremock app worker
                        for i in $(seq 1 60); do
                          if ${COMPOSE} exec -T app python -c \
                            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1)" \
                            >/dev/null 2>&1; then
                            echo 'app готов'; exit 0
                          fi
                          sleep 2
                        done
                        ${COMPOSE} ps
                        ${COMPOSE} logs app
                        exit 1
                    '''
                }
            }
        }

        stage('Static quality gates') {
            steps {
                dir('/workspace') {
                    sh '''
                        ${COMPOSE} run --rm \
                          -v "${HOST_PROJECT_DIR}:/workspace" \
                          app sh -c "python -m compileall -q app tests && ruff check app tests && \
                                     python /workspace/tools/test_policy.py /workspace/student_tests \
                                       --output /workspace/ci-artifacts/test-policy.json"
                    '''
                }
            }
        }

        stage('Reference API tests') {
            steps {
                dir('/workspace') {
                    sh '''
                        ${COMPOSE} run --rm \
                          -e DATABASE_URL=sqlite:////tmp/qa-reference.db \
                          -e ENVIRONMENT=development \
                          -e SECRET_KEY=test-secret-at-least-32-bytes-long! \
                          -e ALLOW_TEST_MUTATIONS=${ALLOW_TEST_MUTATIONS} \
                          -v "${HOST_PROJECT_DIR}/ci-artifacts:/ci-artifacts" \
                          -v "${ALLURE_VOLUME}:/allure-results" \
                          app python -m pytest tests \
                            --alluredir=/allure-results \
                            --junitxml=/ci-artifacts/reference-api-junit.xml \
                            --cov=app --cov-report=term-missing \
                            --cov-report=xml:/ci-artifacts/reference-coverage.xml \
                            --cov-fail-under=70
                    '''
                }
            }
        }

        stage('Student API and integration tests') {
            steps {
                dir('/workspace') {
                    sh '''
                        docker run --rm --init \
                          --network ${COMPOSE_PROJECT_NAME}_default \
                          -v "${HOST_PROJECT_DIR}:/workspace" \
                          -v "${ALLURE_VOLUME}:/allure-results" \
                          -w /workspace \
                          -e BASE_URL=http://app.test:8000 \
                          -e STUDENT_DATABASE_URL=postgresql://qatp:qatp@db:5432/qatp \
                          -e TEST_USER_EMAIL=user@test.com \
                          -e TEST_USER_PASSWORD=Password123! \
                          -e TEST_SUPPORT_KEY=${TEST_SUPPORT_KEY} \
                          -e ALLOW_TEST_MUTATIONS=${ALLOW_TEST_MUTATIONS} \
                          python:3.12-slim sh -c "pip install -r student_tests/requirements.txt --quiet && \
                            python -m pytest student_tests/api student_tests/contract student_tests/integration \
                              --alluredir=/allure-results \
                              --junitxml=/workspace/ci-artifacts/student-api-junit.xml"
                    '''
                }
            }
        }

        stage('Reference E2E: Chromium, Firefox, WebKit + axe') {
            steps {
                dir('/workspace') {
                    sh '''
                        docker run --rm --init --ipc=host \
                          --network ${COMPOSE_PROJECT_NAME}_default \
                          -v "${HOST_PROJECT_DIR}:/workspace" \
                          -v "${ALLURE_VOLUME}:/allure-results" \
                          -w /workspace/e2e \
                          -e BASE_URL=http://app.test:8000 \
                          mcr.microsoft.com/playwright/python:v1.61.0-noble \
                          sh -c "pip install -r requirements.txt --quiet && \
                            python -m pytest --browser chromium --browser firefox --browser webkit \
                              --alluredir=/allure-results \
                              --junitxml=/workspace/ci-artifacts/reference-e2e-junit.xml \
                              --tracing=retain-on-failure --screenshot=only-on-failure \
                              --video=retain-on-failure --output=/workspace/e2e/test-results"
                    '''
                }
            }
        }

        stage('Student UI: Chromium, Firefox, WebKit + axe') {
            steps {
                dir('/workspace') {
                    sh '''
                        docker run --rm --init --ipc=host \
                          --network ${COMPOSE_PROJECT_NAME}_default \
                          -v "${HOST_PROJECT_DIR}:/workspace" \
                          -v "${ALLURE_VOLUME}:/allure-results" \
                          -w /workspace \
                          -e BASE_URL=http://app.test:8000 \
                          -e TEST_USER_EMAIL=user@test.com \
                          -e TEST_USER_PASSWORD=Password123! \
                          -e TEST_SUPPORT_KEY=${TEST_SUPPORT_KEY} \
                          mcr.microsoft.com/playwright/python:v1.61.0-noble \
                          sh -c "pip install -r student_tests/requirements.txt --quiet && \
                            python -m pytest student_tests/ui \
                              --browser chromium --browser firefox --browser webkit \
                              --alluredir=/allure-results \
                              --junitxml=/workspace/ci-artifacts/student-ui-junit.xml \
                              --tracing=retain-on-failure --screenshot=only-on-failure \
                              --video=retain-on-failure --output=/workspace/student_tests/test-results"
                    '''
                }
            }
        }

        stage('Mutation score') {
            when {
                expression { params.RUN_MUTATIONS }
            }
            steps {
                dir('/workspace') {
                    sh '''
                        docker run --rm --init --ipc=host \
                          --network ${COMPOSE_PROJECT_NAME}_default \
                          -v "${HOST_PROJECT_DIR}:/workspace" \
                          -w /workspace \
                          -e BASE_URL=http://app.test:8000 \
                          -e TEST_USER_EMAIL=user@test.com \
                          -e TEST_USER_PASSWORD=Password123! \
                          -e TEST_SUPPORT_KEY=${TEST_SUPPORT_KEY} \
                          -e ALLOW_TEST_MUTATIONS=${ALLOW_TEST_MUTATIONS} \
                          mcr.microsoft.com/playwright/python:v1.61.0-noble \
                          sh -c "pip install -r student_tests/requirements.txt --quiet && \
                            python tools/mutation_score.py \
                              --config student_tests/mutations.json \
                              --output ci-artifacts/mutation-score.json"
                    '''
                }
            }
        }

        stage('Performance p95 gate') {
            when {
                expression { params.RUN_PERFORMANCE }
            }
            steps {
                dir('/workspace') {
                    sh '''
                        docker run --rm --init \
                          --network ${COMPOSE_PROJECT_NAME}_default \
                          -v "${HOST_PROJECT_DIR}/performance:/performance:ro" \
                          -v "${HOST_PROJECT_DIR}/ci-artifacts:/ci-artifacts" \
                          -w /performance \
                          -e PERF_P95_LIMIT_MS=${PERF_P95_LIMIT_MS} \
                          -e PERF_FAILURE_RATIO=${PERF_FAILURE_RATIO} \
                          -e PERF_MIN_REQUESTS=${PERF_MIN_REQUESTS} \
                          locustio/locust:2.46.0 \
                          -f locustfile.py --headless --host http://app.test:8000 \
                          -u 5 -r 5 -t 20s --csv=/ci-artifacts/performance \
                          --html=/ci-artifacts/performance.html --only-summary
                    '''
                }
            }
        }
    }

    post {
        always {
            dir('/workspace') {
                // Summary is generated even when a test stage fails. This
                // keeps the defect list and partial metrics visible in history.
                sh(returnStatus: true, script: '''
                    mkdir -p "${HOST_PROJECT_DIR}/${ALLURE_RESULTS_DIR}"
                    docker run --rm \
                      -v "${ALLURE_VOLUME}:/src:ro" \
                      -v "${HOST_PROJECT_DIR}/${ALLURE_RESULTS_DIR}:/dst" \
                      alpine:3.20 sh -c 'cp -a /src/. /dst/ 2>/dev/null || true'
                    ${COMPOSE} run --rm \
                      -v "${HOST_PROJECT_DIR}:/workspace" \
                      -e BUILD_NUMBER=${BUILD_NUMBER} \
                      -e BRANCH_NAME=${BRANCH_NAME} \
                      -e GIT_COMMIT=${GIT_COMMIT} \
                      -e CI_STARTED_AT=${CI_STARTED_AT} \
                      app python /workspace/tools/build_quality_summary.py \
                        --artifacts /workspace/ci-artifacts \
                        --history /app/quality-history
                ''')
                junit testResults: 'ci-artifacts/**/*junit*.xml', allowEmptyResults: true
                archiveArtifacts artifacts: 'ci-artifacts/**,allure-results/**,e2e/test-results/**,student_tests/test-results/**',
                    allowEmptyArchive: true, fingerprint: true
                sh(returnStatus: true, script: '''
                    ${COMPOSE} down --remove-orphans
                    docker volume rm \
                      "${COMPOSE_PROJECT_NAME}_pgdata" \
                      "${COMPOSE_PROJECT_NAME}_avatar_uploads" \
                      "${COMPOSE_PROJECT_NAME}_allure_results" \
                      "${COMPOSE_PROJECT_NAME}_allure_reports" >/dev/null 2>&1 || true
                ''')
            }
        }
    }
}
