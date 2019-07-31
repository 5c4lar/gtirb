"""GTIRB IR module

Sample usage:
    Opening a GTIRB Protobuf file and loading it into an IR instance:
        ir = IR.load_protobuf('filename.gtir')

    Writing the IR instance as a Protobuf file:
        IR.save_protobuf('filename.gtir')

"""
import IR_pb2

from .auxdata import AuxData, AuxDataContainer
from .module import Module


class IR(AuxDataContainer):
    """A complete internal representation consisting of multiple Modules.

    Attributes:
        aux_data: Auxilary data associated with this IR
        modules: list of Modules contained in the IR
        uuid: the UUID of this Node

    """
    def __init__(self, modules=list(), aux_data=dict(), uuid=None):
        # Note: modules are decoded before the aux data, since the UUID
        # decoder checks Node's cache.
        self.modules = list(modules)
        super().__init__(aux_data, uuid)

    @classmethod
    def _decode_protobuf(cls, proto_ir, uuid):
        aux_data = (
            (key, AuxData._from_protobuf(val))
            for key, val in proto_ir.aux_data_container.aux_data.items()
        )
        modules = (Module._from_protobuf(m) for m in proto_ir.modules)
        return cls(modules, aux_data, uuid)

    def _to_protobuf(self):
        proto_ir = IR_pb2.IR()
        proto_ir.uuid = self.uuid.bytes
        proto_ir.modules.extend(m._to_protobuf() for m in self.modules)
        proto_ir.aux_data_container.CopyFrom(super()._to_protobuf())
        return proto_ir

    @staticmethod
    def load_protobuf_file(protobuf_file):
        """Load IR from Protobuf file object

        Parameters:
            protobuf_file: a file object containing the Protobuf

        Returns:
            Python GTIRB IR object

        """
        ir = IR_pb2.IR()
        ir.ParseFromString(protobuf_file.read())
        return IR._from_protobuf(ir)

    @staticmethod
    def load_protobuf(file_name):
        """Load IR from Protobuf file at path

        Parameters:
            file_name: the path to the Protobuf file

        Returns:
            Python GTIRB IR object

        """
        with open(file_name, 'rb') as f:
            return IR.load_protobuf_file(f)

    def save_protobuf_file(self, protobuf_file):
        """Save IR to Protobuf file object

        Parameters:
            protobuf_file: target file object

        """
        protobuf_file.write(self._to_protobuf().SerializeToString())

    def save_protobuf(self, file_name):
        """Save IR to Protobuf file at path

        Parameters:
            file_name: the target path of the Protobuf file

        """
        with open(file_name, 'wb') as f:
            self.save_protobuf_file(f)
