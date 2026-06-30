import json
from pathlib import Path


DOCUMENT_SERVICES_PATH = Path(__file__).resolve().parents[1] / "config" / "document_services.json"


class DocumentServiceError(ValueError):
    pass


class UnsupportedDocumentServiceError(DocumentServiceError):
    pass


class DisabledDataEvaluatorServiceError(DocumentServiceError):
    pass


def normalize_service_id(service_id):
    if service_id is None:
        raise UnsupportedDocumentServiceError("Document service id is required")

    normalized_service_id = str(service_id).strip().upper()

    if not normalized_service_id:
        raise UnsupportedDocumentServiceError("Document service id is required")

    return normalized_service_id


def load_document_services(path=DOCUMENT_SERVICES_PATH):
    with Path(path).open("r", encoding="utf-8") as inventory_file:
        services = json.load(inventory_file)

    if not isinstance(services, list):
        raise DocumentServiceError("Document services inventory must be a list")

    return services


def get_document_service(service_id, path=DOCUMENT_SERVICES_PATH):
    normalized_service_id = normalize_service_id(service_id)

    for service in load_document_services(path):
        if service.get("id") == normalized_service_id:
            return service

    raise UnsupportedDocumentServiceError(
        f"Document service '{normalized_service_id}' is not supported"
    )


def is_data_evaluator_enabled(service_id, path=DOCUMENT_SERVICES_PATH):
    service = get_document_service(service_id, path)
    return bool(service.get("data_evaluator_enabled", False))


def validate_data_evaluator_service(service_id, path=DOCUMENT_SERVICES_PATH):
    service = get_document_service(service_id, path)
    normalized_service_id = service.get("id", normalize_service_id(service_id))

    if not service.get("data_evaluator_enabled", False):
        raise DisabledDataEvaluatorServiceError(
            f"Document service '{normalized_service_id}' is disabled for DATA evaluator"
        )

    return service
