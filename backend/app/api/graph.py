"""图谱路由（M3-5）：文档数据流图谱 + R1-R4 推理结果。

契约：GET /documents/{id}/graph → {data: GraphPayload}（对齐 DATA_CONTRACT 4.7）。
薄层：仅参数校验 + 调 graph_service。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.graph_service import build_graph_for_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{document_id}/graph")
async def get_document_graph(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """返回指定文档的数据流图谱（含 R1-R4 riskPaths/suggestions）。"""
    try:
        payload = build_graph_for_document(db=db, document_id=document_id)
    except HTTPException:
        raise
    return {"data": payload.dump_dict()}
