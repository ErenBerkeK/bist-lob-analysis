"""Quick probe of BIST ITCH pcap - validates message layout and symbol names."""
import struct
from collections import Counter

PCAP_PATH = r"C:\Users\HUAWEI\Desktop\bist-lob-analysis\data\itch-pri-20260427.pcap"
UDP_OFFSET = 42
MOLD_HEADER = 20
MAX_PACKETS = 500_000


def u16(b, o): return struct.unpack_from(">H", b, o)[0]
def u32(b, o): return struct.unpack_from(">I", b, o)[0]
def u64(b, o): return struct.unpack_from(">Q", b, o)[0]
def i32(b, o): return struct.unpack_from(">i", b, o)[0]


def clean_alpha(raw: bytes) -> str:
    return raw.split(b"\x00")[0].decode("latin-1", errors="ignore").strip()


def main():
    msg_types = Counter()
    symbols = {}
    add_samples = []

    with open(PCAP_PATH, "rb") as f:
        f.read(24)  # global header
        packets = 0
        while packets < MAX_PACKETS:
            hdr = f.read(16)
            if len(hdr) < 16:
                break
            incl_len = struct.unpack("<I", hdr[8:12])[0]
            pkt = f.read(incl_len)
            packets += 1

            if len(pkt) < UDP_OFFSET + MOLD_HEADER:
                continue
            buf = pkt
            msg_count = u16(buf, UDP_OFFSET + 18)
            if msg_count == 0 or msg_count > 500:
                continue
            off = UDP_OFFSET + MOLD_HEADER

            for _ in range(msg_count):
                if off + 2 > len(buf):
                    break
                msg_len = u16(buf, off)
                data_off = off + 2
                if data_off + msg_len > len(buf):
                    break
                msg = buf[data_off : data_off + msg_len]
                if not msg:
                    break
                mt = chr(msg[0])
                msg_types[mt] += 1

                if mt == "R" and msg_len >= 95:
                    ob_id = u32(msg, 5)
                    sym = clean_alpha(msg[9:41])
                    price_dec = u16(msg, 89)
                    fin_prod = msg[85]
                    symbols[ob_id] = (sym, fin_prod, price_dec)

                if mt == "A" and msg_len >= 34 and len(add_samples) < 5:
                    add_samples.append({
                        "ob_id": u32(msg, 13),
                        "side": chr(msg[17]),
                        "qty": u64(msg, 22),
                        "price_raw": i32(msg, 30),
                        "sym": symbols.get(u32(msg, 13), ("?", 0, 2))[0],
                        "dec": symbols.get(u32(msg, 13), ("?", 0, 2))[2],
                    })

                off = data_off + msg_len

    print(f"Packets scanned: {packets}")
    print(f"Top message types: {msg_types.most_common(15)}")
    print(f"\nDirectory entries: {len(symbols)}")

    spot = [s for s in symbols.values() if s[0].endswith(".E")]
    fut = [s for s in symbols.values() if s[0].startswith("F_")]
    print(f"Spot (.E): {len(spot)}, Futures (F_): {len(fut)}")
    print("\nSample spot symbols:")
    for s in sorted(set(x[0] for x in spot))[:15]:
        print(f"  {s}")
    print("\nSample futures symbols:")
    for s in sorted(set(x[0] for x in fut))[:15]:
        print(f"  {s}")

    print("\nSample Add Order messages:")
    for s in add_samples:
        dec = s["dec"] if s["dec"] < 256 else 2
        price = s["price_raw"] / (10 ** dec)
        print(f"  {s['sym']} side={s['side']} qty={s['qty']} price={price:.4f}")


if __name__ == "__main__":
    main()
