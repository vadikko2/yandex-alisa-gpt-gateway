from __future__ import annotations

import cqrs
from cqrs.bootstrap import requests as bootstrap
from cqrs.container.dependency_injector import DependencyInjectorCQRSContainer
from dependency_injector import containers, providers

from alice_gateway.infrastructure.adapters.language_model import (
    OpenAICompatibleLanguageModel,
    StubLanguageModel,
)
from alice_gateway.infrastructure.dialogs import DialogStore
from alice_gateway.service.handlers.commands.reply import ReplyToUtteranceCommandHandler
from alice_gateway.service.models.commands.reply import ReplyToUtteranceCommand
from alice_gateway.shared.settings import Settings, load_settings


def build_language_model(settings: Settings) -> StubLanguageModel | OpenAICompatibleLanguageModel:
    if settings.llm_api_key.strip():
        return OpenAICompatibleLanguageModel(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
        )
    return StubLanguageModel()


def commands_mapper(mapper: cqrs.RequestMap) -> None:
    mapper.bind(ReplyToUtteranceCommand, ReplyToUtteranceCommandHandler)


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(load_settings)
    language_model = providers.Singleton(build_language_model, settings=settings)
    dialogs = providers.Singleton(DialogStore)
    reply_to_utterance_handler = providers.Factory(
        ReplyToUtteranceCommandHandler,
        language_model=language_model,
        dialogs=dialogs,
        settings=settings,
    )


def build_mediator(container: Container) -> cqrs.RequestMediator:
    cqrs_container = DependencyInjectorCQRSContainer()
    cqrs_container.attach_external_container(container)
    return bootstrap.bootstrap(di_container=cqrs_container, commands_mapper=commands_mapper)


def build_container() -> Container:
    return Container()
