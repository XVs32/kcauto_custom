"""LZString.compressToUTF16 的移植(只給測試產生固定資料用,執行期不需要)。"""


def compress_utf16(text: str) -> str:
    return _compress(text, 15, lambda a: chr(a + 32)) + " "


def _compress(uncompressed, bits_per_char, to_char):
    if uncompressed is None:
        return ""
    dictionary, to_create = {}, {}
    w = ""
    enlarge, size, nbits = 2, 3, 2
    data, val, pos = [], 0, 0

    def put(bit):
        nonlocal val, pos
        val = (val << 1) | bit
        if pos == bits_per_char - 1:
            pos = 0
            data.append(to_char(val))
            val = 0
        else:
            pos += 1

    def put_bits(value, count):
        for _ in range(count):
            put(value & 1)
            value >>= 1

    def emit(token):
        nonlocal enlarge, nbits
        if token in to_create:
            first = ord(token[0])
            if first < 256:
                put_bits(0, nbits)
                put_bits(first, 8)
            else:
                put_bits(1, nbits)
                put_bits(first, 16)
            enlarge -= 1
            if enlarge == 0:
                enlarge = 1 << nbits
                nbits += 1
            del to_create[token]
        else:
            put_bits(dictionary[token], nbits)

    for c in uncompressed:
        if c not in dictionary:
            dictionary[c] = size
            size += 1
            to_create[c] = True
        wc = w + c
        if wc in dictionary:
            w = wc
        else:
            emit(w)
            enlarge -= 1
            if enlarge == 0:
                enlarge = 1 << nbits
                nbits += 1
            dictionary[wc] = size
            size += 1
            w = c
    if w != "":
        emit(w)
        enlarge -= 1
        if enlarge == 0:
            enlarge = 1 << nbits
            nbits += 1
    put_bits(2, nbits)                      # 結束標記
    while True:                             # 補滿最後一個字元
        val <<= 1
        if pos == bits_per_char - 1:
            data.append(to_char(val))
            break
        pos += 1
    return "".join(data)
