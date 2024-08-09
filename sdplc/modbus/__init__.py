from typing import List, Literal

from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder


def encoder(
    value: int | float,
    size: Literal[16, 32, 64] = 16,
    byte_order: Endian = Endian.BIG,
    word_order: Endian = Endian.BIG,
):
    builder = BinaryPayloadBuilder(byteorder=byte_order, wordorder=word_order)
    if isinstance(value, int):
        if size == 16:
            builder.add_16bit_int(value)
        elif size == 32:
            builder.add_32bit_int(value)
        elif size == 64:
            builder.add_64bit_int(value)
    elif isinstance(value, float):
        if size == 16:
            raise ValueError("16 bit float is not supported.")
        if size == 32:
            builder.add_32bit_float(value)
        elif size == 64:
            builder.add_64bit_float(value)
    return builder.to_registers()


def decoder(
    bits: List[int],
    type: Literal["int", "float"] = "float",
    byte_order: Endian = Endian.BIG,
    word_order: Endian = Endian.BIG,
):
    """
    decoder Decode the bits to int or float.

    Decode the bits to int or float based on the given size and format.

    Args:
        bits (List[int]): the bits to be decoded.
        size (Literal[16, 32, 64], optional): the length of the bits. Defaults to 16.
        format (Literal[&quot;int&quot;, &quot;float&quot;], optional): the type of the value. Defaults to "float".

    Returns:
        int | float: The decoded value.
    """
    decoder = BinaryPayloadDecoder.fromRegisters(
        bits, byteorder=byte_order, wordorder=word_order
    )
    if type == "float":
        if len(bits) == 1:
            raise ValueError("16 bit float is not supported.")
        elif len(bits) == 2:
            return decoder.decode_32bit_float()
        elif len(bits) == 4:
            return decoder.decode_64bit_float()
    if type == "int":
        if len(bits) == 1:
            return decoder.decode_16bit_int()
        elif len(bits) == 2:
            return decoder.decode_32bit_int()
        elif len(bits) == 4:
            return decoder.decode_64bit_int()
    raise ValueError(
        f"Invalid length of bits,  expected 16, 32 or 64, but got {len(bits)}."
    )
