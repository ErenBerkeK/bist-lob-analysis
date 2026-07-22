"""Find MoldUDP packets with actual ITCH messages."""
import struct
from collections import Counter

PCAP_PATH = r"C:\Users\HUAWEI\Desktop\bist-lob-analysis\data\itch-pri-20260427.pcap"


def u16(b, o):
    return struct.unpack_from(">H", b, o)[0]


def main():
    msg_types = Counter()
    symbols = {}
    packets_with_msgs = 0
    total = 0

    with open(PCAP_PATH, "rb") as f:
        f.read(24)
        while total < 2_000_000:
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
            udp_start = ip_start + ihl
            payload = pkt[udp_start + 8 :]
            if len(payload) < 22:
                continue

            msg_count = u16(payload, 18)
            if msg_count == 0 or msg_count > 500:
                continue
            packets_with_msgs += 1
            off = 20
            for _ in range(msg_count):
                if off + 2 > len(payload):
                    break
                msg_len = u16(payload, off)
                data_off = off + 2
                if data_off + msg_len > len(payload):
                    break
                msg = payload[data_off : data_off + msg_len]
                if msg:
                    mt = chr(msg[0])
                    msg_types[mt] += 1
                    if mt == "R" and msg_len >= 95:
                        ob_id = struct.unpack_from(">I", msg, 5)[0]
                        sym = msg[9:41].split(b"\x00")[0].decode("latin-1").strip()
                        price_dec = struct.unpack_from(">H", msg, 89)[0]
                        symbols[ob_id] = sym
                off = data_off + msg_len

            if packets_with_msgs == 1:
                print("First packet with messages found at packet index", total)

    print(f"Scanned packets: {total}")
    print(f"Packets with ITCH messages: {packets_with_msgs}")
    print(f"Message types: {msg_types.most_common(20)}")
    print(f"Directory symbols: {len(symbols)}")
    spots = sorted({s for s in symbols.values() if ".E" in s})[:10]
    futs = sorted({s for s in symbols.values() if s.startswith("F_")})[:10]
    print("Sample spots:", spots)
    print("Sample futures:", futs)


if __name__ == "__main__":
    main()
