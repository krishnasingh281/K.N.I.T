"""GrpcStage: drop-in for RemoteStage over gRPC/HTTP2."""
import grpc
import torch

from . import stage_pb2 as pb
from . import stage_pb2_grpc as pbg
from .wire import pack, unpack

OPTS = [("grpc.max_send_message_length", 256 << 20),
        ("grpc.max_receive_message_length", 256 << 20)]


class GrpcStage:
    def __init__(self, target: str, codec: str = "none"):
        self.url = self.target = target
        self.codec, self.last_compute_ms = codec, 0.0
        self.stub = pbg.StageStub(grpc.insecure_channel(target, options=OPTS))
        i = self.stub.Info(pb.Empty(), timeout=60)
        self.info = {"start": i.start, "end": i.end, "first": i.first, "last": i.last}

    def alive(self) -> bool:
        try:
            self.stub.Info(pb.Empty(), timeout=1.0)
            return True
        except grpc.RpcError:
            return False

    def reset(self, sid):
        self.stub.Reset(pb.SessionReq(sid=sid))

    def rollback(self, sid, pos):
        self.stub.Rollback(pb.RollbackReq(sid=sid, pos=pos))

    def close(self, sid):
        self.stub.Close(pb.SessionReq(sid=sid))

    def forward(self, sid, x: torch.Tensor):
        raw, m = pack(x, self.codec)
        r = self.stub.Forward(pb.Tensor(sid=sid, dtype=m["dtype"], shape=m["shape"], data=raw))
        self.last_compute_ms = r.compute_ms
        return unpack(r.data, r.dtype, list(r.shape))