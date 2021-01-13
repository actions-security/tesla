FROM registry.gitlab.com/actions-security/suite/docker-base:latest

COPY ./commons /suite/commons
COPY ./tesla /suite/tesla

WORKDIR /suite/tesla

ENV ACTIONS_PRODUCTION true

RUN conda devenv

RUN chmod +x tools/entrypoint.sh

ENTRYPOINT ["tools/entrypoint.sh"]
