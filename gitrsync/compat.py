import enum

try:
    # Use enum.IntFlag if available
    IntFlag = enum.IntFlag
except AttributeError:
    class IntFlag(int, enum.Enum):
        """Incomplete compatible IntFlag"""

        def __repr__(self):
            cls = type(self)
            if self._name_ is not None:
                return '<%s.%s: %r>' % (cls.__name__, self._name_, self._value_)
            else:
                return '<%s: %r>' % (cls.__name__, self._value_)

        def __str__(self):
            cls = type(self)
            if self._name_ is not None:
                return '%s.%s' % (cls.__name__, self._name_)
            else:
                return '%s.%r' % (cls.__name__, self._value_)

        @classmethod
        def _get_member(cls, value):
            """Get a member from its value or create a pseudo one"""
            if value in cls._value2member_map_:
                return cls._value2member_map_[value]

            obj = int.__new__(cls, value)
            obj._name_ = None
            obj._value_ = value

            return obj

        def __contains__(self, item):
            if not isinstance(item, int):
                return NotImplemented

            return self & item == item

        def __or__(self, other):
            cls = type(self)

            if isinstance(other, cls):
                value = self.value | other.value
            elif isinstance(other, int):
                value = self.value | other
            else:
                return NotImplemented

            return cls._get_member(value)

        def __and__(self, other):
            cls = type(self)

            if isinstance(other, cls):
                flags = self.value & other.value
            elif isinstance(other, int):
                flags = self.value & other
            else:
                return NotImplemented

            return cls._get_member(flags)

        def __xor__(self, other):
            cls = type(self)

            if isinstance(other, cls):
                value = self.value ^ other.value
            elif isinstance(other, int):
                value = self.value ^ other
            else:
                return NotImplemented

            return cls._get_member(value)

        __ror__ = __or__
        __rand__ = __or__
        __rxor__ = __xor__
