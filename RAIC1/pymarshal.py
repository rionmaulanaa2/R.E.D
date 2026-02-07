#!/usr/bin/env python3
import io
import struct
from dataclasses import dataclass
from typing import Any, Dict

TYPE_NULL = b"0"
TYPE_NONE = b"N"
TYPE_FALSE = b"F"
TYPE_TRUE = b"T"
TYPE_STOPITER = b"S"
TYPE_ELLIPSIS = b"."
TYPE_INT = b"i"
TYPE_INT64 = b"I"
TYPE_FLOAT = b"f"
TYPE_COMPLEX = b"x"
TYPE_BINARY_FLOAT = b"g"
TYPE_BINARY_COMPLEX = b"y"
TYPE_LONG = b"l"
TYPE_STRING = b"s"
TYPE_INTERNED = b"t"
TYPE_STRINGREF = b"R"
TYPE_TUPLE = b"("
TYPE_LIST = b"["
TYPE_DICT = b"{"
TYPE_CODE = b"c"
TYPE_UNICODE = b"u"
TYPE_UNKNOWN = b"?"
TYPE_SET = b"<"
TYPE_FROZENSET = b">"

UNKNOWN_BYTECODE = 0


class _NULL:
    pass


class LongInt(int):
    pass


@dataclass
class CodeObject:
    co_argcount: int
    co_nlocals: int
    co_stacksize: int
    co_flags: int
    co_code: bytes
    co_consts: Any
    co_names: Any
    co_varnames: Any
    co_freevars: Any
    co_cellvars: Any
    co_filename: Any
    co_name: Any
    co_firstlineno: int
    co_lnotab: bytes


class _Marshaller:
    dispatch: Dict[Any, Any] = {}

    def __init__(self, writefunc, opmap=None):
        self._write = writefunc
        self._opmap = opmap or {}

    def dump(self, x):
        try:
            self.dispatch[type(x)](self, x)
        except KeyError:
            for tp in type(x).mro():
                func = self.dispatch.get(tp)
                if func:
                    break
            else:
                raise ValueError("unmarshallable object")
            func(self, x)

    def w_long64(self, x: int) -> None:
        self.w_long(x)
        self.w_long(x >> 32)

    def w_long(self, x: int) -> None:
        a = x & 0xFF
        x >>= 8
        b = x & 0xFF
        x >>= 8
        c = x & 0xFF
        x >>= 8
        d = x & 0xFF
        self._write(bytes((a, b, c, d)))

    def w_short(self, x: int) -> None:
        self._write(bytes((x & 0xFF, (x >> 8) & 0xFF)))

    def dump_none(self, x):
        self._write(TYPE_NONE)

    dispatch[type(None)] = dump_none

    def dump_bool(self, x: bool):
        if x:
            self._write(TYPE_TRUE)
        else:
            self._write(TYPE_FALSE)

    dispatch[bool] = dump_bool

    def dump_stopiter(self, x):
        if x is not StopIteration:
            raise ValueError("unmarshallable object")
        self._write(TYPE_STOPITER)

    dispatch[type(StopIteration)] = dump_stopiter

    def dump_ellipsis(self, x):
        self._write(TYPE_ELLIPSIS)

    try:
        dispatch[type(Ellipsis)] = dump_ellipsis
    except NameError:
        pass

    def dump_int(self, x: int):
        y = x >> 31
        if y and y != -1:
            self._write(TYPE_INT64)
            self.w_long64(x)
        else:
            self._write(TYPE_INT)
            self.w_long(x)

    dispatch[int] = dump_int

    def dump_long(self, x: int):
        self._write(TYPE_LONG)
        sign = 1
        if x < 0:
            sign = -1
            x = -x
        digits = []
        while x:
            digits.append(x & 0x7FFF)
            x = x >> 15
        self.w_long(len(digits) * sign)
        for d in digits:
            self.w_short(d)

    dispatch[LongInt] = dump_long

    def dump_float(self, x: float):
        self._write(TYPE_FLOAT)
        s = repr(x).encode("ascii")
        self._write(bytes((len(s),)))
        self._write(s)

    dispatch[float] = dump_float

    def dump_complex(self, x: complex):
        self._write(TYPE_COMPLEX)
        s = repr(x.real).encode("ascii")
        self._write(bytes((len(s),)))
        self._write(s)
        s = repr(x.imag).encode("ascii")
        self._write(bytes((len(s),)))
        self._write(s)

    dispatch[complex] = dump_complex

    def dump_string(self, x: bytes):
        self._write(TYPE_STRING)
        self.w_long(len(x))
        self._write(x)

    dispatch[bytes] = dump_string

    def dump_unicode(self, x: str):
        self._write(TYPE_UNICODE)
        s = x.encode("utf8")
        self.w_long(len(s))
        self._write(s)

    dispatch[str] = dump_unicode

    def dump_tuple(self, x: tuple):
        self._write(TYPE_TUPLE)
        self.w_long(len(x))
        for item in x:
            self.dump(item)

    dispatch[tuple] = dump_tuple

    def dump_list(self, x: list):
        self._write(TYPE_LIST)
        self.w_long(len(x))
        for item in x:
            self.dump(item)

    dispatch[list] = dump_list

    def dump_dict(self, x: dict):
        self._write(TYPE_DICT)
        for key, value in x.items():
            self.dump(key)
            self.dump(value)
        self._write(TYPE_NULL)

    dispatch[dict] = dump_dict

    def dump_code(self, x: CodeObject):
        self._write(TYPE_CODE)
        self.w_long(x.co_argcount)
        self.w_long(x.co_nlocals)
        self.w_long(x.co_stacksize)
        self.w_long(x.co_flags)
        self.dump(self._transform_opcode(x.co_code))
        self.dump(x.co_consts)
        self.dump(x.co_names)
        self.dump(x.co_varnames)
        self.dump(x.co_freevars)
        self.dump(x.co_cellvars)
        self.dump(x.co_filename)
        self.dump(x.co_name)
        self.w_long(x.co_firstlineno)
        self.dump(x.co_lnotab)

    dispatch[CodeObject] = dump_code

    def _transform_opcode(self, x: bytes) -> bytes:
        if not self._opmap:
            return x

        opcode = bytearray(x)
        c = 0
        while c < len(opcode):
            n = self._opmap.get(opcode[c], opcode[c])
            opcode[c] = n
            if n < 90:
                c += 1
            else:
                c += 3

        return bytes(opcode)

    def dump_set(self, x: set):
        self._write(TYPE_SET)
        self.w_long(len(x))
        for each in x:
            self.dump(each)

    dispatch[set] = dump_set

    def dump_frozenset(self, x: frozenset):
        self._write(TYPE_FROZENSET)
        self.w_long(len(x))
        for each in x:
            self.dump(each)

    dispatch[frozenset] = dump_frozenset


class _Unmarshaller:
    dispatch: Dict[Any, Any] = {}

    def __init__(self, readfunc):
        self._read = readfunc
        self._stringtable = []

    def load(self):
        c = self._read(1)
        if not c:
            raise EOFError
        try:
            return self.dispatch[c](self)
        except KeyError:
            raise ValueError("bad marshal code: %r (%d)" % (c, c[0]))

    def r_short(self) -> int:
        lo = self._read(1)[0]
        hi = self._read(1)[0]
        x = lo | (hi << 8)
        if x & 0x8000:
            x = x - 0x10000
        return x

    def r_long(self) -> int:
        s = self._read(4)
        a, b, c, d = s[0], s[1], s[2], s[3]
        x = a | (b << 8) | (c << 16) | (d << 24)
        if d & 0x80 and x > 0:
            x = -((1 << 32) - x)
            return int(x)
        return x

    def r_long64(self) -> int:
        s = self._read(8)
        a, b, c, d, e, f, g, h = s
        x = a | (b << 8) | (c << 16) | (d << 24)
        x = x | (e << 32) | (f << 40) | (g << 48) | (h << 56)
        if h & 0x80 and x > 0:
            x = -((1 << 64) - x)
        return x

    def load_null(self):
        return _NULL

    dispatch[TYPE_NULL] = load_null

    def load_none(self):
        return None

    dispatch[TYPE_NONE] = load_none

    def load_true(self):
        return True

    dispatch[TYPE_TRUE] = load_true

    def load_false(self):
        return False

    dispatch[TYPE_FALSE] = load_false

    def load_stopiter(self):
        return StopIteration

    dispatch[TYPE_STOPITER] = load_stopiter

    def load_ellipsis(self):
        return Ellipsis

    dispatch[TYPE_ELLIPSIS] = load_ellipsis

    dispatch[TYPE_INT] = r_long

    dispatch[TYPE_INT64] = r_long64

    def load_long(self):
        size = self.r_long()
        sign = 1
        if size < 0:
            sign = -1
            size = -size
        x = 0
        for i in range(size):
            d = self.r_short()
            x = x | (d << (i * 15))
        return LongInt(x * sign)

    dispatch[TYPE_LONG] = load_long

    def load_float(self):
        n = self._read(1)[0]
        s = self._read(n)
        return float(s.decode("ascii"))

    dispatch[TYPE_FLOAT] = load_float

    def load_complex(self):
        n = self._read(1)[0]
        s = self._read(n)
        real = float(s.decode("ascii"))
        n = self._read(1)[0]
        s = self._read(n)
        imag = float(s.decode("ascii"))
        return complex(real, imag)

    dispatch[TYPE_COMPLEX] = load_complex

    def load_binary_float(self):
        s = self._read(8)
        return struct.unpack("<d", s)[0]

    dispatch[TYPE_BINARY_FLOAT] = load_binary_float

    def load_binary_complex(self):
        s = self._read(16)
        real, imag = struct.unpack("<dd", s)
        return complex(real, imag)

    dispatch[TYPE_BINARY_COMPLEX] = load_binary_complex

    def load_string(self):
        n = self.r_long()
        return self._read(n)

    dispatch[TYPE_STRING] = load_string

    def load_interned(self):
        n = self.r_long()
        ret = self._read(n)
        self._stringtable.append(ret)
        return ret

    dispatch[TYPE_INTERNED] = load_interned

    def load_stringref(self):
        n = self.r_long()
        return self._stringtable[n]

    dispatch[TYPE_STRINGREF] = load_stringref

    def load_unicode(self):
        n = self.r_long()
        s = self._read(n)
        return s.decode("utf8")

    dispatch[TYPE_UNICODE] = load_unicode

    def load_tuple(self):
        return tuple(self.load_list())

    dispatch[TYPE_TUPLE] = load_tuple

    def load_list(self):
        n = self.r_long()
        return [self.load() for _ in range(n)]

    dispatch[TYPE_LIST] = load_list

    def load_dict(self):
        d = {}
        while True:
            key = self.load()
            if key is _NULL:
                break
            value = self.load()
            d[key] = value
        return d

    dispatch[TYPE_DICT] = load_dict

    def load_code(self):
        argcount = self.r_long()
        nlocals = self.r_long()
        stacksize = self.r_long()
        flags = self.r_long()
        code = self.load()
        consts = self.load()
        names = self.load()
        varnames = self.load()
        freevars = self.load()
        cellvars = self.load()
        filename = self.load()
        name = self.load()
        firstlineno = self.r_long()
        lnotab = self.load()
        return CodeObject(
            argcount,
            nlocals,
            stacksize,
            flags,
            code,
            consts,
            names,
            varnames,
            freevars,
            cellvars,
            filename,
            name,
            firstlineno,
            lnotab,
        )

    dispatch[TYPE_CODE] = load_code

    def load_set(self):
        n = self.r_long()
        args = [self.load() for _ in range(n)]
        return set(args)

    dispatch[TYPE_SET] = load_set

    def load_frozenset(self):
        n = self.r_long()
        args = [self.load() for _ in range(n)]
        return frozenset(args)

    dispatch[TYPE_FROZENSET] = load_frozenset


def dump(x, f, opmap=None):
    m = _Marshaller(f.write, opmap)
    m.dump(x)


def load(f):
    um = _Unmarshaller(f.read)
    return um.load()


def loads(content: bytes):
    bio = io.BytesIO(content)
    return load(bio)


def dumps(x, opmap=None) -> bytes:
    bio = io.BytesIO()
    dump(x, bio, opmap)
    bio.seek(0)
    return bio.read()
