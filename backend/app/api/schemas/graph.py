from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    name: str | None
    summary: str | None
    type: str | None


class GraphEdge(BaseModel):
    src: str
    dst: str
    relation: str


class ConceptGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
