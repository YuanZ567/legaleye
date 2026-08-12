"""图谱模块（M3）：networkx 图构建 + R1-R4 推理。

GraphBuilder 负责从抽取的实体/边构建有向图并序列化为契约 GraphPayload；
R1-R4 推理（M3-4）复用本模块的图结构。
"""

from app.graph.builder import GraphBuilder

__all__ = ["GraphBuilder"]
