from __future__ import annotations

import cqrs
from cqrs.container.dependency_injector import DependencyInjectorCQRSContainer
from cqrs.requests.map import RequestMap
from dependency_injector import containers, providers

from alice_gateway.infrastructure.adapters.language_model import StubLanguageModel, TimewebLanguageModel
from alice_gateway.infrastructure.dialogs import DialogStore
from alice_gateway.service.handlers.commands.reply import ReplyToUtteranceCommandHandler
from alice_gateway.service.models.commands.reply import ReplyToUtteranceCommand
from alice_gateway.shared.settings import Settings, load_settings


def build_language_model(settings: Settings) -> StubLanguageModel | TimewebLanguageModel:
    if settings.timeweb_api_key.strip() and settings.timeweb_base_url.strip():
        return TimewebLanguageModel(
            api_key=settings.timeweb_api_key,
            base_url=settings.timeweb_base_url,
            model=settings.timeweb_model,
        )
    return StubLanguageModel()


def build_request_map() -> RequestMap:
    request_map = RequestMap()
    request_map.bind(ReplyToUtteranceCommand, ReplyToUtteranceCommandHandler)
    return request_map


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
    return cqrs.RequestMediator(request_map=build_request_map(), container=cqrs_container)


def build_container() -> Container:
    return Container()
