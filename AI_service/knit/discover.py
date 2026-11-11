import httpx

from .remote import RemoteStage


def discover(orch_http: str, code: str, codec: str = "none"):
    """RemoteStages for the alive stage nodes of one cluster, ordered by layer range."""
    r = httpx.get(f"{orch_http.rstrip('/')}/cluster/{code.strip().upper()}/nodes", timeout=5)
    r.raise_for_status()
    nodes = [n for n in r.json() if n["status"] == "alive" and n.get("start") is not None]
    nodes.sort(key=lambda n: n["start"])
    assert nodes and nodes[0]["start"] == 0, "no stage starting at layer 0"
    for a, b in zip(nodes, nodes[1:]):
        assert a["end"] == b["start"], f"gap/overlap between {a['id']} and {b['id']}"
    assert nodes[-1]["last"], "last stage missing"
    return [RemoteStage(n["url"], codec) for n in nodes]