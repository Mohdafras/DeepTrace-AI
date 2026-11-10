"""Detection history endpoints."""
from fastapi import APIRouter, HTTPException, Response, status
from app.schemas import HistoryRecord, HistoryResponse
from app.services import history_service

router = APIRouter()


@router.get("/history", response_model=HistoryResponse)
def list_history() -> HistoryResponse:
    items = history_service.list_records()
    return HistoryResponse(items=items, total=len(items))


@router.get("/history/{record_id}", response_model=HistoryRecord)
def retrieve_history(record_id: int) -> HistoryRecord:
    record = history_service.get_record(record_id)
    if record is None:
        raise HTTPException(404, "History record not found.")
    return HistoryRecord(**record)


@router.delete("/history/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_history(record_id: int) -> Response:
    if not history_service.delete_record(record_id):
        raise HTTPException(404, "History record not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_history() -> Response:
    history_service.delete_all_records()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
