"""Find correct UDP payload offset in pcap."""
import struct

PCAP_PATH = r"C:\Users\HUAWEI\Desktop\bist-lob-analysis\data\itch-pri-20260427.pcap"


def main():
    with open(PCAP_PATH, "rb") as f:
        gh = f.read(24)
        magic = struct.unpack("<I", gh[:4])[0]
        print(f"Magic: {hex(magic)} (LE={magic == 0xA1B2C3D4}, BE={magic == 0xD4C3B2A1})")
        le = magic in (0xA1B2C3D4, 0xA1B23C4D)

        for pkt_idx in range(20):
            hdr = f.read(16)
            if len(hdr) < 16:
                break
            if le:
                incl_len = struct.unpack("<I", hdr[8:12])[0]
            else:
                incl_len = struct.unpack(">I", hdr[8:12])[0]
            pkt = f.read(incl_len)
            print(f"\nPacket {pkt_idx}: len={len(pkt)}")
            if len(pkt) < 60:
                continue
            # dump first bytes after eth header candidates
            for eth_len in [14, 16, 18]:
                if len(pkt) <= eth_len + 20:
                    continue
                ip_start = eth_len
                ihl = (pkt[ip_start] & 0x0F) * 4
                proto = pkt[ip_start + 9]
                if proto != 17:
                    continue
                udp_start = ip_start + ihl
                if udp_start + 8 > len(pkt):
                    continue
                dst_port = struct.unpack(">H", pkt[udp_start + 2 : udp_start + 4])[0]
                payload = pkt[udp_start + 8 :]
                if len(payload) < 24:
                    continue
                # MoldUDP: session[10], seq[8], count[2]
                sess = payload[:10].decode("latin-1", errors="replace")
                count = struct.unpack(">H", payload[18:20])[0]
                msg_type = chr(payload[20 + 2]) if len(payload) > 22 else "?"
                print(
                    f"  eth={eth_len} iphl={ihl} dst_port={dst_port} "
                    f"payload={len(payload)} session={sess!r} mold_count={count} first_msg={msg_type!r}"
                )


if __name__ == "__main__":
    main()
