def parse_tag(registers, offset, dtype, strlen=0):
    if dtype == "word":
        return registers[offset]

    if dtype == "dword":
        low = registers[offset]
        high = registers[offset + 1]
        return low | (high << 16)

    if dtype == "string":
        chars = []
        for i in range(strlen):
            reg = registers[offset + i]
            chars.append(chr((reg >> 8) & 0xFF))
            chars.append(chr(reg & 0xFF))
        return "".join(chars).rstrip("\x00")

    raise ValueError(f"Unknown dtype: {dtype}")
