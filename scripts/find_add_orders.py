"""Locate Add Order messages and BIST50 symbol pairs in pcap."""
import struct
from collections import Counter

PCAP_PATH = r"C:\Users\HUAWEI\Desktop\bist-lob-analysis\data\itch-pri-20260427.pcap"

BIST50_ROOTS = {
    "AKBNK", "ARCLK", "ASELS", "BIMAS", "EKGYO", "ENKAI", "EREGL", "FROTO",
    "GARAN", "GUBRF", "HEKTS", "ISCTR", "KCHOL", "KOZAA", "KOZAL", "KRDMD",
    "MGROS", "ODAS", "PETKM", "PGSUS", "SAHOL", "SASA", "SISE", "TAVHL",
    "TCELL", "THYAO", "TOASO", "TUPRS", "YKBNK", "EGEEN", "SOKM",
}


def u16(b, o):
    return struct.unpack_from(">H", b, o)[0]


def root(sym: str) -> str:
    s = sym.replace(".E", "")
    if s.startswith("F_"):
        return s[2:6] if len(s) >= 6 else s[2:]
    return s


def main():
    msg_types = Counter()
    symbols = {}
    add_count = 0
    total = 0
    first_add = None

    with open(PCAP_PATH, "rb") as f:
        f.read(24)
        while total < 15_000_000:
            hdr = f.read(16)
            if len(hdr) < 16:
                break
            incl_len = struct.unpack("<I", hdr[8:12])[0]
            pkt = f.read(incl_len)
            total += 1

            if len(pkt) < 42:
                continue
            ip_start = 14
            ihl = (pkt[ip_start] & 0x0F) * 4
            if pkt[ip_start + 9] != 17:
                continue
            payload = pkt[ip_start + ihl + 8 :]
            if len(payload) < 22:
                continue

            msg_count = u16(payload, 18)
            if msg_count == 0 or msg_count > 500:
                continue
            off = 20
            for _ in range(msg_count):
                if off + 2 > len(payload):
                    break
                msg_len = u16(payload, off)
                data_off = off + 2
                if data_off + msg_len > len(payload):
                    break
                msg = payload[data_off : data_off + msg_len]
                if not msg:
                    break
                mt = chr(msg[0])
                msg_types[mt] += 1

                if mt == "R" and msg_len >= 95:
                    ob_id = struct.unpack_from(">I", msg, 5)[0]
                    sym = msg[9:41].split(b"\x00")[0].decode("latin-1").strip()
                    price_dec = struct.unpack_from(">H", msg, 89)[0]
                    symbols[ob_id] = (sym, price_dec)

                if mt == "A":
                    add_count += 1
                    if first_add is None:
                        ob_id = struct.unpack_from(">I", msg, 13)[0]
                        sym = symbols.get(ob_id, ("?", 2))[0]
                        first_add = (total, sym)

                off = data_off + msg_len

    print(f"Scanned packets: {total:,}")
    print(f"Add orders: {add_count:,}")
    print(f"First add: packet={first_add}")
    print(f"Message types: {msg_types.most_common(25)}")

    spot = {s[0]: dec for s in symbols.values() if s[0].endswith(".E")}
    fut = {s[0]: dec for s in symbols.values() if s[0].startswith("F_")}

    pairs = []
    for f_sym in sorted(fut):
        r = root(f_sym)
        spot_sym = f"{r}.E"
        if spot_sym in spot and r in BIST50_ROOTS:
            pairs.append((spot_sym, f_sym))

    print(f"\nBIST50 spot/future pairs found: {len(pairs)}")
    for p in pairs[:15]:
        print(f"  {p[0]} / {p[1]}")


if __name__ == "__main__":
    main()
