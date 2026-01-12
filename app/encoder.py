def encode_value(value, dtype, length=0):
    if dtype == "word":
        return [int(value) & 0xFFFF]

    if dtype == "dword":
        v = int(value)
        low = v & 0xFFFF
        high = (v >> 16) & 0xFFFF
        return [low, high]

    if dtype == "string":
        s = str(value).ljust(length * 2, "\x00")
        regs = []
        for i in range(0, length * 2, 2):
            regs.append((ord(s[i]) << 8) | ord(s[i + 1]))
        return regs

    raise ValueError("Unsupported dtype")
