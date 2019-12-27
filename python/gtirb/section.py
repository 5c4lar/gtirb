import Section_pb2
import typing
import itertools
from enum import Enum
from uuid import UUID

from .block import ByteBlock, CodeBlock, DataBlock
from .node import Node
from .byteinterval import ByteInterval
from .util import SetWrapper


class Section(Node):
    """Represents a named section of the binary.

    Does not directly store the contents of the section, which are
    kept in a :class:`gtirb.ImageByteMap`.

    :ivar name: The section name (E.g. ".text", ".bss", etc).
    :ivar byte_intervals: The :class:`ByteInterval`\\s in this section.
    :ivar flags: The :class:`Section.Flag`\\s this section has.
    """

    class Flag(Enum):
        """A flag representing a known property of a section."""

        Undefined = Section_pb2.SectionFlag.Value(b"Undefined")
        """This value is defined for Protobuf compatibility. Do not use."""

        Readable = Section_pb2.SectionFlag.Value(b"Readable")
        """This section can be read from at runtime."""

        Writable = Section_pb2.SectionFlag.Value(b"Writable")
        """This section can be written to at runtime."""

        Executable = Section_pb2.SectionFlag.Value(b"Executable")
        """This section contains executable code."""

        Loaded = Section_pb2.SectionFlag.Value(b"Loaded")
        """This section is present in memory at runtime."""

        Initialized = Section_pb2.SectionFlag.Value(b"Initialized")
        """This section has bytes allocated to it in the binary file."""

        ThreadLocal = Section_pb2.SectionFlag.Value(b"ThreadLocal")
        """This section is created in memory once per thread."""

    class _ByteIntervalSet(SetWrapper):
        def add(self, v):
            if v._section is not None:
                v._section.byte_intervals.discard(v)
            v._section = self
            return super().add(v)

        def discard(self, v):
            v._section = None
            return super().discard(v)

    def __init__(
        self,
        *,
        name="",  # type: str
        byte_intervals=(),  # type: typing.Iterable[ByteInterval]
        flags=set(),  # type: typing.Iterable[Section.Flag]
        uuid=None,  # type: typing.Optional[UUID]
    ):
        """
        :param name: The name of this section.
        :param byte_intervals: The :class:`ByteInterval`\\s in this section.
        :param flags: The :class:`Section.Flag`\\s this section has.
        :param uuid: The UUID of this ``Section``,
            or None if a new UUID needs generated via :func:`uuid.uuid4`.
            Defaults to None.
        """

        super().__init__(uuid)
        self.name = name  # type: str
        self.byte_intervals = Section._ByteIntervalSet(
            byte_intervals
        )  # type: typing.Set[ByteInterval]
        self.flags = set(flags)  # type: typing.Set[Section.Flag]
        self._module = None  # type: "Module"

    @classmethod
    def _decode_protobuf(cls, proto_section, uuid):
        # type: (Section_pb2.Section, UUID) -> Section
        return cls(
            name=proto_section.name,
            byte_intervals=(
                ByteInterval._from_protobuf(bi)
                for bi in proto_section.byte_intervals
            ),
            flags=(Section.Flag(f) for f in proto_section.section_flags),
            uuid=uuid,
        )

    def _to_protobuf(self):
        # type: () -> Section_pb2.Section
        """Get a Protobuf representation of ``self``."""

        proto_section = Section_pb2.Section()
        proto_section.uuid = self.uuid.bytes
        proto_section.name = self.name
        proto_section.byte_intervals.extend(
            bi._to_protobuf() for bi in self.byte_intervals
        )
        proto_section.section_flags.extend(f.value for f in self.flags)
        return proto_section

    def deep_eq(self, other):
        # type: (typing.Any) -> bool
        # Do not move __eq__. See docstring for Node.deep_eq for more info.
        if not isinstance(other, Section):
            return False
        return (
            self.uuid == other.uuid
            and self.name == other.name
            and len(self.byte_intervals) == len(other.byte_intervals)
            and all(
                self_node.deep_eq(other_node)
                for self_node, other_node in zip(
                    self.byte_intervals, other.byte_intervals
                )
            )
            and self.flags == other.flags
        )

    def __repr__(self):
        # type: () -> str
        return (
            "Section("
            "uuid={uuid!r}, "
            "name={name!r}, "
            "byte_intervals={byte_intervals!r}, "
            "flags=({pretty_flags}), "
            ")".format(
                pretty_flags=", ".join(
                    "Section." + str(f) for f in self.flags
                ),
                **self.__dict__,
            )
        )

    @property
    def module(self):
        # type: () -> "Module"
        """The :class:`Module` this section belongs to."""

        return self._module

    @module.setter
    def module(self, value):
        # type: ("Module") -> None
        if self._module is not None:
            self._module.sections.discard(self)
        if value is not None:
            value.sections.add(self)

    @property
    def byte_blocks(self):
        # type: () -> typing.Iterator[ByteBlock]
        """The :class:`ByteBlock`\\s in this section."""

        return itertools.chain.from_iterable(
            bi.blocks for bi in self.byte_intervals
        )

    @property
    def code_blocks(self):
        # type: () -> typing.Iterator[CodeBlock]
        """The :class:`CodeBlock`\\s in this section."""

        return (b for b in self.byte_blocks if isinstance(b, CodeBlock))

    @property
    def data_blocks(self):
        # type: () -> typing.Iterator[DataBlock]
        """The :class:`DataBlock`\\s in this section."""

        return (b for b in self.byte_blocks if isinstance(b, DataBlock))
