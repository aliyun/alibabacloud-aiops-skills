#!/usr/bin/env python3
"""
pcap_analyze.py - Deep packet capture analysis tool (pure Python/scapy implementation)

SECURITY:
  - Read-only analysis: this script only parses the given capture file and
    NEVER modifies the input file.
  - It is invoked only after explicit user confirmation and processes ONLY
    the file explicitly specified by the user on the command line.
  - Fully offline: it makes no network connections and sends no data
    anywhere; all analysis happens locally.

Analysis dimensions: transfer rate, FIN/RST anomalies, burst retransmissions,
window variation, RTT jitter

Usage:
  python3 pcap_analyze.py <pcap_file> [--src <IP>] [--dst <IP>] [--port <PORT>]
                         [--output <md_file>]

Output: Markdown analysis report
"""

import argparse
import sys
import os
import re
import struct
from collections import defaultdict
from datetime import datetime

try:
    from scapy.all import rdpcap, TCP, UDP, IP, ICMP, DNS, Raw, IPerror, ICMPerror
    from scapy.all import conf as scapy_conf
    scapy_conf.use_pcap = True
except ImportError:
    print("[ERROR] Required dependency 'scapy' is missing.\n"
          "        Install it with: pip3 install scapy\n"
          "        Then re-run this script.", file=sys.stderr)
    sys.exit(2)

# -- Utility functions -----------------------------------------------------------

def parse_float(s):
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def parse_int(s):
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


def safe_div(a, b, default=0.0):
    try:
        return a / b if b else default
    except (ZeroDivisionError, TypeError):
        return default


# -- IKE algorithm mapping tables ------------------------------------------------

IKEV1_ENC_ALGOS = {
    1: "DES-CBC", 2: "3DES-CBC", 3: "RC5", 4: "IDEA", 5: "CAST",
    6: "Blowfish", 7: "3IDEA", 8: "DES-IV64",
    127: "AES-CBC",
}
IKEV1_HASH_ALGOS = {1: "MD5", 2: "SHA1", 3: "Tiger", 4: "SHA2-256", 5: "SHA2-384", 6: "SHA2-512"}
IKEV1_AUTH_METHODS = {
    1: "Pre-Shared Key", 2: "DSS Signatures", 3: "RSA Signatures",
    4: "RSA Encryption", 5: "Revised RSA Encryption",
    64221: "Pre-Shared Key", 65001: "SM2 Signatures",
}
DH_GROUPS = {
    1: "MODP 768", 2: "MODP 1024", 5: "MODP 1536",
    14: "MODP 2048", 15: "MODP 3072", 16: "MODP 4096",
    17: "MODP 6144", 18: "MODP 8192",
    19: "ECP 256", 20: "ECP 384", 21: "ECP 521",
    22: "DHCP 1024-160", 23: "DHCP 2048-224",
    24: "DHCP 2048-256",
    65001: "SM2 (Chinese National Crypto)",
}
IKEV2_ENC_ALGOS = {
    1: "DES-IV64", 2: "DES", 3: "3DES", 4: "RC5", 5: "IDEA", 6: "CAST",
    7: "Blowfish", 8: "3IDEA", 9: "DES-IV32",
    12: "AES-CBC", 13: "AES-CTR",
    20: "AES-GCM (12)", 21: "AES-GCM (16)",
}
IKEV2_INTEGRITY_ALGOS = {
    0: "NONE", 1: "AUTH-HMAC-MD5-96", 2: "AUTH-HMAC-SHA1-96",
    3: "AUTH-DES-MAC", 4: "AUTH-KPDK-MD5",
    5: "AUTH-AES-XCBC-96", 6: "AUTH-HMAC-MD5-128",
    7: "AUTH-HMAC-SHA1-160", 8: "AUTH-AES-CMAC-96",
    9: "AUTH-AES-128-GMAC", 10: "AUTH-AES-192-GMAC",
    11: "AUTH-AES-256-GMAC",
    12: "AUTH-HMAC-SHA2-256-128", 13: "AUTH-HMAC-SHA2-384-192",
    14: "AUTH-HMAC-SHA2-512-256",
}
IKEV2_PRF_ALGOS = {
    0: "NONE", 1: "PRF-HMAC-MD5", 2: "PRF-HMAC-SHA1",
    3: "PRF-HMAC-TIGER", 4: "PRF-AES128-XCBC",
    5: "PRF-HMAC-SHA2-256", 6: "PRF-HMAC-SHA2-384",
    7: "PRF-HMAC-SHA2-512", 8: "PRF-AES-CMAC",
}
NOTIFY_TYPEMAP = {
    1: "INVALID-PAYLOAD-TYPE", 2: "DOI-NOT-SUPPORTED",
    3: "INVALID-SITUATION", 4: "INVALID-FLAGS",
    5: "INVALID-MESSAGE-ID", 6: "INVALID-PROTOCOL-ID",
    7: "INVALID-SPI", 8: "INVALID-PROPOSAL-SYNTAX",
    9: "INVALID-TRANSFORM-ID", 10: "ATTRIBUTES-NOT-SUPPORTED",
    11: "INVALID-KEY-INFORMATION", 12: "INVALID-ID-INFORMATION",
    13: "INVALID-CERT-ENCODING", 14: "NO-PROPOSAL-CHOSEN",
    15: "BAD-PROPOSAL-SYNTAX", 16: "PAYLOAD-MALFORMED",
    17: "INVALID-CERTIFICATE", 18: "CERT-REVOKED",
    19: "CERT-NOT-YET-VALID", 20: "CERT-EXPIRED",
    24: "AUTHENTICATION-FAILED",
    25: "UNSUPPORTED_CRITICAL_PAYLOAD",
    34: "NO-PROPOSAL-CHOSEN", 35: "TS-UNACCEPTABLE",
    36: "INVALID_SYNTAX", 37: "INVALID_MESSAGE_INFORMATIONAL",
    38: "INVALID_SPI", 39: "FAILED-CP-REQUIRED",
    40: "INVALID-SELECTORS", 41: "UNACCEPTABLE-ADDRESSES",
    42: "UNEXPECTED-NAT-DETECTED", 43: "USE-TRANSPORT-MODE-NOTIFY",
    44: "INVALID_PACKET_FIELDS",
    16384: "INITIAL-CONTACT", 16385: "SET-WINDOW-SIZE",
    16386: "ADDITIONAL-TS-POSSIBLE", 16387: "REKEY-SA",
    16388: "NAT-DETECTION-SOURCE-IP", 16389: "NAT-DETECTION-DESTINATION-IP",
    16390: "COOKIE", 16391: "USE-TRANSPORT-MODE",
    16392: "HTTP-CERT-LOOKUP", 16393: "REAUTH",
    16394: "CHILD-SA-NOT-FOUND",
}

IKEV1_EXCH_TYPES = {
    0: "None", 1: "Base", 2: "Identity Protection (Main Mode)",
    3: "Authentication Only", 4: "Aggressive",
    5: "Informational (Notify)", 6: "Transaction (Quick Mode)",
}
IKEV2_EXCH_TYPES = {
    32: "IKEv2 SA_INIT", 33: "IKEv2 AUTH",
    34: "IKEv2 CREATE_CHILD_SA", 35: "IKEv2 INFORMATIONAL",
}


# -- ISAKMP/IKE binary parser -----------------------------------------------------

def _tcp_flags_str(tcp_layer):
    """Convert scapy TCP flags into a readable string"""
    flags = []
    fl = tcp_layer.flags
    if fl & 0x20: flags.append("U")
    if fl & 0x10: flags.append("A")
    if fl & 0x08: flags.append("P")
    if fl & 0x04: flags.append("R")
    if fl & 0x02: flags.append("S")
    if fl & 0x01: flags.append("F")
    return ".".join(flags) if flags else ""


def _extract_sni(raw_payload):
    """Extract the SNI from raw TLS ClientHello bytes"""
    try:
        data = bytes(raw_payload)
        if len(data) < 5:
            return ""
        # TLS record: content_type(1) + version(2) + length(2)
        if data[0] != 0x16:  # not handshake
            return ""
        # Handshake: type(1) + length(3)
        hs_start = 5
        if len(data) < hs_start + 4:
            return ""
        if data[hs_start] != 0x01:  # not ClientHello
            return ""
        # ClientHello: version(2) + random(32) + session_id_len(1)
        pos = hs_start + 1 + 2 + 32
        if pos >= len(data):
            return ""
        sid_len = data[pos]
        pos += 1 + sid_len
        # cipher_suites_len(2)
        if pos + 2 > len(data):
            return ""
        cs_len = struct.unpack("!H", data[pos:pos+2])[0]
        pos += 2 + cs_len
        # compression_methods_len(1)
        if pos >= len(data):
            return ""
        cm_len = data[pos]
        pos += 1 + cm_len
        # extensions_len(2)
        if pos + 2 > len(data):
            return ""
        ext_len = struct.unpack("!H", data[pos:pos+2])[0]
        pos += 2
        ext_end = pos + ext_len
        while pos + 4 <= ext_end and pos + 4 <= len(data):
            ext_type = struct.unpack("!H", data[pos:pos+2])[0]
            ext_data_len = struct.unpack("!H", data[pos+2:pos+4])[0]
            pos += 4
            if ext_type == 0:  # SNI extension
                if pos + 2 > len(data):
                    return ""
                sni_list_len = struct.unpack("!H", data[pos:pos+2])[0]
                sni_pos = pos + 2
                if sni_pos + 3 > len(data):
                    return ""
                sni_type = data[sni_pos]
                sni_name_len = struct.unpack("!H", data[sni_pos+1:sni_pos+3])[0]
                sni_pos += 3
                if sni_type == 0 and sni_pos + sni_name_len <= len(data):
                    return data[sni_pos:sni_pos+sni_name_len].decode("ascii", errors="ignore")
                return ""
            pos += ext_data_len
    except Exception:
        pass
    return ""


def _extract_ike_notify_type(payload_data):
    """Extract the notify type value from an ISAKMP Notify payload"""
    try:
        data = bytes(payload_data)
        if len(data) < 12:
            return None
        # Notify payload header:
        # Next Payload(1) + Reserved(1) + Length(2) + DOI(4) + Protocol(1) + SPI Size(1) + Notify Msg Type(2)
        notify_msg_type = struct.unpack("!H", data[8:10])[0]
        return notify_msg_type
    except Exception:
        return None


def _parse_isakmp_proposals(raw_data, ike_version_num):
    """Parse proposals inside the ISAKMP SA payload
    and return a list of proposal dicts
    """
    proposals = []
    try:
        data = bytes(raw_data)
        if len(data) < 28:
            return proposals
        # ISAKMP header: 28 bytes
        # ISPI(8) + RSPI(8) + NextPayload(1) + Version(1) + ExchType(1) + Flags(1) + MsgID(4) + Length(4)
        next_payload = data[16]
        isakmp_len = struct.unpack("!I", data[24:28])[0]
        offset = 28
        while next_payload != 0 and offset < len(data) and offset < isakmp_len:
            if offset + 4 > len(data):
                break
            np_next = data[offset]
            payload_len = struct.unpack("!H", data[offset+2:offset+4])[0]
            if payload_len < 4 or offset + payload_len > len(data):
                break
            # SA payload = type 1
            if next_payload == 1:
                sub_proposals = _parse_sa_payload(data[offset:offset+payload_len], ike_version_num)
                proposals.extend(sub_proposals)
            next_payload = np_next
            offset += payload_len
    except Exception:
        pass
    return proposals


def _parse_sa_payload(sa_data, ike_version_num):
    """Parse the SA payload and extract the inner Proposal and Transform sub-payloads"""
    proposals = []
    try:
        if len(sa_data) < 12:
            return proposals
        # SA payload body: DOI(4) + Situation(4) + then Proposal sub-payloads
        offset = 12  # skip header(4) + DOI(4) + Situation(4)
        # The rest contains Proposal payloads (type=2) chained
        # But they're nested: SA -> Proposal -> Transform
        # In ISAKMP, sub-payloads are NOT in the next-payload chain;
        # they are embedded within the parent payload.
        # We need to walk through the SA payload body to find Proposal sub-payloads.
        # Actually in ISAKMP, the Proposal payloads follow the SA header
        # using the generic payload header format.
        while offset + 4 <= len(sa_data):
            prop_next = sa_data[offset]
            prop_len = struct.unpack("!H", sa_data[offset+2:offset+4])[0]
            if prop_len < 4 or offset + prop_len > len(sa_data):
                break
            if prop_next == 2 or sa_data[offset+1] == 2:
                # This is a Proposal payload (type 2)
                prop = _parse_proposal(sa_data[offset:offset+prop_len], ike_version_num)
                if prop:
                    proposals.append(prop)
            offset += prop_len
            if prop_next == 0:
                break
    except Exception:
        pass
    return proposals


def _parse_proposal(prop_data, ike_version_num):
    """Parse a Proposal payload"""
    proposal = {
        "is_request": True,
        "exchange_type": None,
        "ike_version": str(ike_version_num),
        "encryption": None,
        "hash": None,
        "auth_method": None,
        "prf": None,
        "integrity": None,
        "dh_group": None,
        "key_length": None,
        "life_duration": None,
        "notify_type": None,
        "vendor_ids": [],
        "nat_t": False,
        "dpd": False,
    }
    try:
        if len(prop_data) < 8:
            return None
        # Proposal payload header:
        # NextPayload(1) + Reserved(1) + Length(2) + ProposalNum(1) + ProtocolID(1) + SPISize(1) + NumTransforms(1)
        num_transforms = prop_data[7]
        spi_size = prop_data[6]
        # Skip to transforms: header(8) + SPI(spi_size)
        offset = 8 + spi_size
        for _ in range(num_transforms):
            if offset + 4 > len(prop_data):
                break
            xform_next = prop_data[offset]
            xform_len = struct.unpack("!H", prop_data[offset+2:offset+4])[0]
            if xform_len < 4 or offset + xform_len > len(prop_data):
                break
            xform = _parse_transform(prop_data[offset:offset+xform_len], ike_version_num)
            if xform:
                for k, v in xform.items():
                    if v is not None and proposal.get(k) is None:
                        proposal[k] = v
            offset += xform_len
            if xform_next == 0:
                break
    except Exception:
        pass
    return proposal


def _parse_transform(xform_data, ike_version_num):
    """Parse a Transform payload and extract algorithm information"""
    result = {
        "encryption": None, "hash": None, "auth_method": None,
        "prf": None, "integrity": None, "dh_group": None,
        "key_length": None, "life_duration": None,
    }
    try:
        if len(xform_data) < 8:
            return None
        # Transform payload header:
        # NextPayload(1) + Reserved(1) + Length(2) + TransformNum(1) + TransformID(1) + Reserved2(2)
        transform_id = xform_data[5]

        if ike_version_num == 1:
            # IKEv1: Transform ID = encryption algorithm
            result["encryption"] = IKEV1_ENC_ALGOS.get(transform_id, f"Unknown({transform_id})")
            # Attributes follow: Type(2) + Value(2) for each (Type-Value format, AF bit set)
            offset = 8
            while offset + 4 <= len(xform_data):
                attr_type_raw = struct.unpack("!H", xform_data[offset:offset+2])[0]
                attr_type = attr_type_raw & 0x7FFF  # strip AF bit
                is_tv = bool(attr_type_raw & 0x8000)  # AF=1 means Type-Value format
                if is_tv:
                    attr_value = struct.unpack("!H", xform_data[offset+2:offset+4])[0]
                    if attr_type == 14:  # Key Length
                        result["key_length"] = attr_value
                    elif attr_type == 11:  # Hash Algorithm
                        result["hash"] = IKEV1_HASH_ALGOS.get(attr_value, f"Unknown({attr_value})")
                    elif attr_type == 3:  # Authentication Method
                        result["auth_method"] = IKEV1_AUTH_METHODS.get(attr_value, f"Unknown({attr_value})")
                    elif attr_type == 4:  # Group Description (DH)
                        result["dh_group"] = DH_GROUPS.get(attr_value, f"Unknown({attr_value})")
                    elif attr_type == 12:  # Life Type
                        pass
                    elif attr_type == 13:  # Life Duration
                        result["life_duration"] = attr_value
                    offset += 4
                else:
                    # Type-Length-Value format
                    if offset + 4 > len(xform_data):
                        break
                    attr_len = struct.unpack("!H", xform_data[offset+2:offset+4])[0]
                    offset += 4 + attr_len
        elif ike_version_num == 2:
            # IKEv2: Transform ID has different meaning based on transform type
            # Transform header: NextPayload(1)+Reserved(1)+Length(2)+Reserved(1)+TransformType(1)+Reserved2(2)
            transform_type = xform_data[5]
            # IKEv2 transform types: 1=Encryption, 2=PRF, 3=Integrity, 4=DH
            if transform_type == 1:  # Encryption
                result["encryption"] = IKEV2_ENC_ALGOS.get(transform_id, f"Unknown({transform_id})")
            elif transform_type == 2:  # PRF
                result["prf"] = IKEV2_PRF_ALGOS.get(transform_id, f"Unknown({transform_id})")
            elif transform_type == 3:  # Integrity
                result["integrity"] = IKEV2_INTEGRITY_ALGOS.get(transform_id, f"Unknown({transform_id})")
            elif transform_type == 4:  # DH
                result["dh_group"] = DH_GROUPS.get(transform_id, f"Unknown({transform_id})")
            # IKEv2 attributes: Type(2) + Length(2) + Value(variable)
            offset = 8
            while offset + 4 <= len(xform_data):
                attr_type = struct.unpack("!H", xform_data[offset:offset+2])[0]
                attr_len = struct.unpack("!H", xform_data[offset+2:offset+4])[0]
                if offset + 4 + attr_len > len(xform_data):
                    break
                if attr_len == 2:
                    attr_value = struct.unpack("!H", xform_data[offset+4:offset+6])[0]
                    if attr_type == 14:  # Key Length
                        result["key_length"] = attr_value
                offset += 4 + attr_len
    except Exception:
        pass
    return result


# -- BPF-like filter matching -----------------------------------------------------

def _match_filter(pkt, filter_expr):
    """Simple BPF filter supporting ip.src, ip.dst, tcp.port, udp.port, icmp and other basic filters"""
    if not filter_expr:
        return True
    # Use scapy's built-in match_filter (if available) or parse manually
    parts = filter_expr.split(" && ")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("ip.addr=="):
            ip_val = part.split("==")[1]
            if not _pkt_has_ip(pkt):
                return False
            if pkt[IP].src != ip_val and pkt[IP].dst != ip_val:
                return False
        elif part.startswith("ip.src=="):
            ip_val = part.split("==")[1]
            if not _pkt_has_ip(pkt):
                return False
            if pkt[IP].src != ip_val:
                return False
        elif part.startswith("ip.dst=="):
            ip_val = part.split("==")[1]
            if not _pkt_has_ip(pkt):
                return False
            if pkt[IP].dst != ip_val:
                return False
        elif part.startswith("tcp.port=="):
            port_val = int(part.split("==")[1])
            if not pkt.haslayer(TCP):
                return False
            if pkt[TCP].sport != port_val and pkt[TCP].dport != port_val:
                return False
        elif part.startswith("udp.port=="):
            port_val = int(part.split("==")[1])
            if not pkt.haslayer(UDP):
                return False
            if pkt[UDP].sport != port_val and pkt[UDP].dport != port_val:
                return False
        elif part == "icmp":
            if not pkt.haslayer(ICMP):
                return False
        elif part == "dns":
            if not pkt.haslayer(DNS):
                return False
        elif part == "tcp":
            if not pkt.haslayer(TCP):
                return False
        elif part.startswith("tcp.flags.syn==1"):
            if not pkt.haslayer(TCP):
                return False
            if not (pkt[TCP].flags & 0x02):
                return False
        elif part.startswith("tcp.flags.fin==1") or part.startswith("tcp.flags.reset==1"):
            if not pkt.haslayer(TCP):
                return False
            if part.startswith("tcp.flags.fin==1"):
                if not (pkt[TCP].flags & 0x01):
                    return False
            else:
                if not (pkt[TCP].flags & 0x04):
                    return False
        elif part.startswith("tcp.window_size"):
            if not pkt.haslayer(TCP):
                return False
            # tcp.window_size==0 check
            if "==0" in part:
                if pkt[TCP].window != 0:
                    return False
        elif part.startswith("tcp.len>0"):
            if not pkt.haslayer(TCP):
                return False
            tcp_payload_len = len(pkt[TCP].payload)
            if tcp_payload_len <= 0:
                return False
        elif part.startswith("icmp.type==3") and "icmp.code==4" in part:
            if not pkt.haslayer(ICMP):
                return False
            if pkt[ICMP].type != 3 or pkt[ICMP].code != 4:
                return False
        # Composite condition: (tcp.flags.fin==1 or tcp.flags.reset==1)
        elif part.startswith("(tcp.flags.fin==1 or tcp.flags.reset==1)"):
            if not pkt.haslayer(TCP):
                return False
            if not ((pkt[TCP].flags & 0x01) or (pkt[TCP].flags & 0x04)):
                return False
        elif part.startswith("(tcp.analysis.keep_alive || tcp.analysis.keep_alive_ack)"):
            # TCP keepalive: TCP len=0 or 1, ACK flag set, no data
            if not pkt.haslayer(TCP):
                return False
            if not (pkt[TCP].flags & 0x10):  # ACK must be set
                return False
            tcp_payload = bytes(pkt[TCP].payload)
            if len(tcp_payload) > 1:
                return False
        elif part.startswith("udp.port==500 || udp.port==4500"):
            if not pkt.haslayer(UDP):
                return False
            if pkt[UDP].sport not in (500, 4500) and pkt[UDP].dport not in (500, 4500):
                return False
        elif part.startswith("(udp.port==500 || udp.port==4500) && ip.src"):
            if not pkt.haslayer(UDP):
                return False
            if pkt[UDP].sport not in (500, 4500) and pkt[UDP].dport not in (500, 4500):
                return False
            if not _pkt_has_ip(pkt):
                return False
    return True


def _pkt_has_ip(pkt):
    return pkt.haslayer(IP)


# -- Single-pass pcap processor ----------------------------------------------------

class PcapProcessor:
    """Single pass over the pcap, collecting all data required for analysis"""

    def __init__(self, pcap_file, filter_expr=None):
        self.pcap_file = pcap_file
        self.filter_expr = filter_expr
        self.packets = []
        self.first_ts = None
        self.last_ts = None
        self.total_packets = 0
        self.total_bytes = 0
        # TCP streams: key=(min_ip,min_port,max_ip,max_port)
        self.tcp_streams = defaultdict(lambda: {
            "packets": [],
            "syn_time": None,
            "syn_ack_time": None,
        })
        # Per-packet collected data
        self.pkt_sizes = []
        self.fin_rst_packets = []
        self.zero_windows = []
        self.keepalives = []
        self.icmp_records = []
        self.icmp_frag_needed = []
        self.tcp_mss_values = []
        self.dns_records = []
        self.tls_records = []
        self.tcp_syn_packets = []
        self.ike_packets = []
        self.ike_raw_proposals = []
        # Window sizes per source IP
        self.window_sizes_by_src = defaultdict(list)
        # Throughput per second per source IP
        self.throughput_by_src = defaultdict(lambda: defaultdict(int))
        # TCP flags distribution
        self.tcp_flags_dist = defaultdict(int)
        # RTT samples
        self.rtt_samples = []
        # Conversations
        self.conversations = defaultdict(lambda: {"bytes_a_b": 0, "bytes_b_a": 0, "frames": 0, "frames_a_b": 0, "frames_b_a": 0, "start": None, "end": None})
        # IO stat (per-second)
        self.io_stat = defaultdict(lambda: {"packets": 0, "bytes": 0})
        # Per-second throughput (all packets from a given src)
        self.per_second_bytes = defaultdict(lambda: defaultdict(int))

    def process(self):
        """Read and process all packets"""
        print("[INFO] Reading pcap file...", file=sys.stderr)
        try:
            self.packets = rdpcap(self.pcap_file)
        except FileNotFoundError:
            print(f"[ERROR] pcap file not found: {self.pcap_file}. Check the file path and try again.", file=sys.stderr)
            sys.exit(1)
        except PermissionError:
            print(f"[ERROR] pcap file is not readable (permission denied): {self.pcap_file}. Fix the permissions and try again.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Failed to parse pcap file (corrupted or not a valid pcap file): {self.pcap_file}. Detail: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"[INFO] {len(self.packets)} packets in total, starting analysis...", file=sys.stderr)

        base_time = None
        for idx, pkt in enumerate(self.packets):
            self.total_packets += 1
            pkt_len = len(pkt)
            self.total_bytes += pkt_len

            # Timestamp
            ts = float(pkt.time)
            if self.first_ts is None or ts < self.first_ts:
                self.first_ts = ts
            if self.last_ts is None or ts > self.last_ts:
                self.last_ts = ts
            if base_time is None:
                base_time = ts
            rel_time = ts - base_time

            # IO stat
            sec_bucket = int(rel_time)
            self.io_stat[sec_bucket]["packets"] += 1
            self.io_stat[sec_bucket]["bytes"] += pkt_len

            if not _match_filter(pkt, self.filter_expr):
                continue

            self.pkt_sizes.append(pkt_len)

            # Dispatch by protocol
            if pkt.haslayer(TCP):
                self._process_tcp(pkt, rel_time, idx)
            if pkt.haslayer(UDP):
                self._process_udp(pkt, rel_time, idx)
            if pkt.haslayer(ICMP):
                self._process_icmp(pkt, rel_time, idx)
            if pkt.haslayer(DNS):
                self._process_dns(pkt, rel_time, idx)

        # Post-processing: RTT computed from SYN/SYN-ACK pairs
        self._compute_rtt()
        # Post-processing: retransmission / out-of-order / duplicate ACK from TCP stream analysis
        self._compute_tcp_stream_analysis()

    def _process_tcp(self, pkt, rel_time, idx):
        tcp = pkt[TCP]
        ip = pkt[IP] if pkt.haslayer(IP) else None
        if not ip:
            return

        src, dst = ip.src, ip.dst
        sport, dport = tcp.sport, tcp.dport
        flags = tcp.flags
        payload_len = len(tcp.payload)
        flags_str = _tcp_flags_str(tcp)

        # TCP flags distribution
        self.tcp_flags_dist[flags_str] += 1

        # FIN/RST
        is_fin = bool(flags & 0x01)
        is_rst = bool(flags & 0x04)
        if is_fin or is_rst:
            self.fin_rst_packets.append({
                "frame": str(idx + 1),
                "time": rel_time,
                "src": src,
                "dst": dst,
                "sport": str(sport),
                "dport": str(dport),
                "flags": flags_str,
                "len": payload_len,
                "is_fin": is_fin,
                "is_rst": is_rst,
            })

        # Zero window
        if tcp.window == 0:
            self.zero_windows.append({
                "frame": str(idx + 1),
                "time": rel_time,
                "src": src,
                "dst": dst,
                "sport": str(sport),
                "dport": str(dport),
            })

        # Window sizes by source
        self.window_sizes_by_src[src].append((rel_time, tcp.window))

        # Throughput by source (only data packets)
        if payload_len > 0:
            self.throughput_by_src[src][int(rel_time)] += payload_len
            self.per_second_bytes[src][int(rel_time)] += payload_len

        # SYN / SYN-ACK detection
        is_syn = bool(flags & 0x02)
        is_ack = bool(flags & 0x10)
        if is_syn:
            self.tcp_syn_packets.append({
                "frame": str(idx + 1),
                "time": rel_time,
                "src": src,
                "dst": dst,
                "sport": str(sport),
                "dport": str(dport),
                "is_syn": True,
                "is_ack": is_ack,
            })
            # Extract MSS from TCP options
            for opt_name, opt_val in tcp.options:
                if opt_name == "MSS" and opt_val is not None:
                    self.tcp_mss_values.append({
                        "frame": str(idx + 1),
                        "time": rel_time,
                        "src": src,
                        "dst": dst,
                        "sport": str(sport),
                        "dport": str(dport),
                        "mss": int(opt_val),
                    })

        # TCP keepalive detection: ACK set, payload len 0 or 1
        if is_ack and payload_len <= 1 and not is_syn and not is_fin and not is_rst:
            # Heuristic: keepalive if seq = expected_seq - 1
            self.keepalives.append({
                "frame": str(idx + 1),
                "time": rel_time,
                "src": src,
                "dst": dst,
                "sport": str(sport),
                "dport": str(dport),
                "len": payload_len,
                "is_keepalive": True,
                "is_keepalive_ack": False,
            })

        # TLS detection from raw payload
        if payload_len > 0:
            self._process_tls(pkt, rel_time, idx, src, dst, sport, dport)

        # Conversations
        pkt_len = len(pkt)
        conv_key = self._conv_key(src, sport, dst, dport)
        conv = self.conversations[conv_key]
        conv["frames"] += 1
        if (src, sport) <= (dst, dport):
            conv["bytes_a_b"] += pkt_len
            conv["frames_a_b"] += 1
        else:
            conv["bytes_b_a"] += pkt_len
            conv["frames_b_a"] += 1
        if conv["start"] is None or rel_time < conv["start"]:
            conv["start"] = rel_time
        if conv["end"] is None or rel_time > conv["end"]:
            conv["end"] = rel_time

    def _process_udp(self, pkt, rel_time, idx):
        udp = pkt[UDP]
        ip = pkt[IP] if pkt.haslayer(IP) else None
        if not ip:
            return
        src, dst = ip.src, ip.dst
        sport, dport = udp.sport, udp.dport

        # IKE detection and parsing
        if sport in (500, 4500) or dport in (500, 4500):
            self._process_ike(pkt, rel_time, idx, src, dst, sport, dport)

        # Conversations for UDP
        conv_key = self._conv_key(src, sport, dst, dport)
        conv = self.conversations[conv_key]
        conv["frames"] += 1
        pkt_len = len(pkt)
        if (src, sport) <= (dst, dport):
            conv["bytes_a_b"] += pkt_len
            conv["frames_a_b"] += 1
        else:
            conv["bytes_b_a"] += pkt_len
            conv["frames_b_a"] += 1
        if conv["start"] is None or rel_time < conv["start"]:
            conv["start"] = rel_time
        if conv["end"] is None or rel_time > conv["end"]:
            conv["end"] = rel_time

    def _process_dns(self, pkt, rel_time, idx):
        if not pkt.haslayer(DNS):
            return
        ip = pkt[IP] if pkt.haslayer(IP) else None
        if not ip:
            return
        dns = pkt[DNS]
        src, dst = ip.src, ip.dst
        udp = pkt[UDP] if pkt.haslayer(UDP) else None
        udp_port = str(udp.sport) if udp else ""

        is_response = bool(dns.qr)
        rcode = str(dns.rcode) if is_response else ""
        truncated = bool(dns.tc)

        # Extract query name
        query_name = ""
        query_type = ""
        if dns.qdcount and dns.qd:
            qd = dns.qd
            if hasattr(qd, 'qname'):
                qname = qd.qname
                if isinstance(qname, bytes):
                    qname = qname.decode("ascii", errors="ignore")
                query_name = qname.rstrip(".")
            if hasattr(qd, 'qtype'):
                query_type = str(qd.qtype)

        self.dns_records.append({
            "frame": str(idx + 1),
            "time": rel_time,
            "src": src,
            "dst": dst,
            "udp_port": udp_port,
            "id": str(dns.id),
            "query_name": query_name,
            "query_type": query_type,
            "is_response": is_response,
            "rcode": rcode,
            "truncated": truncated,
        })

    def _process_tls(self, pkt, rel_time, idx, src, dst, sport, dport):
        """Detect TLS handshake messages from the TCP payload"""
        tcp = pkt[TCP]
        raw = bytes(tcp.payload)
        if len(raw) < 5:
            return
        # TLS record header: content_type(1) + version(2) + length(2)
        content_type = raw[0]
        version_raw = struct.unpack("!H", raw[1:3])[0]
        record_len = struct.unpack("!H", raw[3:5])[0]

        # Only process handshake records (content_type=22)
        if content_type != 22:
            # Check for alert (content_type=21)
            if content_type == 21 and len(raw) >= 7:
                alert_level = raw[5]
                alert_desc = raw[6]
                self.tls_records.append({
                    "frame": str(idx + 1),
                    "time": rel_time,
                    "src": src,
                    "dst": dst,
                    "sport": str(sport),
                    "dport": str(dport),
                    "handshake_type": "",
                    "version": f"0x{version_raw:04x}",
                    "server_name": "",
                    "alert_message": str(alert_desc),
                    "ciphersuite": "",
                })
            return

        if len(raw) < 6:
            return
        # Handshake header: type(1) + length(3)
        hs_type = raw[5]
        version_str = f"0x{version_raw:04x}"

        server_name = ""
        ciphersuite = ""
        alert_message = ""

        # ClientHello (type=1)
        if hs_type == 1:
            server_name = _extract_sni(raw)
        # ServerHello (type=2)
        elif hs_type == 2 and len(raw) >= 44:
            # ServerHello: after handshake header(4) + version(2) + random(32) + session_id_len(1) + session_id + cipher_suite(2)
            pos = 5 + 2 + 32  # after record header + hs header + version + random
            if pos < len(raw):
                sid_len = raw[pos]
                pos += 1 + sid_len
                if pos + 2 <= len(raw):
                    cs = struct.unpack("!H", raw[pos:pos+2])[0]
                    ciphersuite = f"0x{cs:04x}"

        self.tls_records.append({
            "frame": str(idx + 1),
            "time": rel_time,
            "src": src,
            "dst": dst,
            "sport": str(sport),
            "dport": str(dport),
            "handshake_type": str(hs_type),
            "version": version_str,
            "server_name": server_name,
            "alert_message": alert_message,
            "ciphersuite": ciphersuite,
        })

    def _process_icmp(self, pkt, rel_time, idx):
        if not pkt.haslayer(ICMP):
            return
        ip = pkt[IP] if pkt.haslayer(IP) else None
        if not ip:
            return
        icmp = pkt[ICMP]
        src, dst = ip.src, ip.dst

        type_map = {
            0: "Echo Reply", 3: "Destination Unreachable",
            5: "Redirect", 8: "Echo Request", 11: "Time Exceeded",
            12: "Parameter Problem", 13: "Timestamp", 14: "Timestamp Reply",
        }
        code_map = {
            3: {
                0: "Network Unreachable", 1: "Host Unreachable",
                2: "Protocol Unreachable", 3: "Port Unreachable",
                4: "Fragmentation Needed (PMTU)", 5: "Source Route Failed",
                9: "Network Administratively Prohibited",
                10: "Host Administratively Prohibited",
                13: "Communication Administratively Prohibited",
            },
            11: {0: "TTL Exceeded in Transit", 1: "Fragment Reassembly Time Exceeded"},
            5: {0: "Network Redirect", 1: "Host Redirect"},
        }

        icmp_type = str(icmp.type)
        icmp_code = str(icmp.code)
        type_name = type_map.get(icmp.type, f"Type {icmp.type}")
        code_name = code_map.get(icmp.type, {}).get(icmp.code, f"Code {icmp.code}")

        # Extract next-hop MTU for type 3 code 4
        next_hop_mtu = None
        if icmp.type == 3 and icmp.code == 4:
            # The unused field in ICMP header contains the next-hop MTU (lower 16 bits)
            next_hop_mtu = icmp.unused if hasattr(icmp, 'unused') else None
            if next_hop_mtu is not None:
                next_hop_mtu = int(next_hop_mtu)
            self.icmp_frag_needed.append({
                "frame": str(idx + 1),
                "time": rel_time,
                "src": src,
                "dst": dst,
                "type": icmp_type,
                "code": icmp_code,
                "next_hop_mtu": next_hop_mtu,
            })

        self.icmp_records.append({
            "frame": str(idx + 1),
            "time": rel_time,
            "src": src,
            "dst": dst,
            "type": icmp_type,
            "code": icmp_code,
            "type_name": type_name,
            "code_name": code_name,
            "next_hop_mtu": next_hop_mtu,
        })

    def _process_ike(self, pkt, rel_time, idx, src, dst, sport, dport):
        """Handle IKE/ISAKMP packets"""
        udp = pkt[UDP]
        raw = bytes(udp.payload)
        if len(raw) < 28:
            return

        # Parse ISAKMP header (28 bytes)
        isakmp_len = struct.unpack("!I", raw[24:28])[0]
        version_byte = raw[17]
        major_ver = (version_byte >> 4) & 0x0F
        minor_ver = version_byte & 0x0F
        exch_type = raw[18]
        flags_byte = raw[19]

        # SPI
        init_spi = raw[0:8].hex()
        resp_spi = raw[8:16].hex()

        # Exchange type name
        if major_ver == 1:
            exchtype_name = IKEV1_EXCH_TYPES.get(exch_type, str(exch_type))
        elif major_ver == 2:
            exchtype_name = IKEV2_EXCH_TYPES.get(exch_type, str(exch_type))
        else:
            exchtype_name = str(exch_type)

        # Flags
        flags_str = ""
        if flags_byte & 0x01:
            flags_str += "Encryption "
        if flags_byte & 0x02:
            flags_str += "Commit "
        if flags_byte & 0x04:
            flags_str += "Authentication-Only "
        flags_str = flags_str.strip()

        # Check for Notify payload
        notify_type_name = ""
        next_payload = raw[16]
        offset = 28
        while next_payload != 0 and offset + 4 <= len(raw):
            np_next = raw[offset]
            payload_len = struct.unpack("!H", raw[offset+2:offset+4])[0]
            if payload_len < 4 or offset + payload_len > len(raw):
                break
            if next_payload == 11:  # Notify payload type
                if offset + 10 <= len(raw):
                    notify_msg_type = struct.unpack("!H", raw[offset+8:offset+10])[0]
                    notify_type_name = NOTIFY_TYPEMAP.get(notify_msg_type, str(notify_msg_type))
                break
            next_payload = np_next
            offset += payload_len

        self.ike_packets.append({
            "frame": str(idx + 1),
            "time": rel_time,
            "src": src,
            "dst": dst,
            "sport": str(sport),
            "dport": str(dport),
            "length": len(pkt),
            "init_spi": init_spi,
            "resp_spi": resp_spi,
            "exchtype": exchtype_name,
            "flags": flags_str,
            "notify_type": notify_type_name,
            "ike_version": str(major_ver),
        })

        # Parse SA proposals from request packets (non-encrypted, has SA payload)
        if not (flags_byte & 0x01):  # not encrypted
            # Check if there's an SA payload (type 1)
            next_p = raw[16]
            off = 28
            while next_p != 0 and off + 4 <= len(raw):
                np_n = raw[off]
                pl = struct.unpack("!H", raw[off+2:off+4])[0]
                if pl < 4 or off + pl > len(raw):
                    break
                if next_p == 1:  # SA payload
                    prop = _parse_isakmp_proposals(raw[off:off+pl], major_ver)
                    for p in prop:
                        p["is_request"] = True
                        p["exchange_type"] = exchtype_name
                        p["ike_version"] = str(major_ver)
                    self.ike_raw_proposals.extend(prop)
                    break
                next_p = np_n
                off += pl

    def _conv_key(self, src, sport, dst, dport):
        """Generate the conversation key, normalizing both directions to the same key"""
        a = (src, str(sport))
        b = (dst, str(dport))
        if a <= b:
            return (src, str(sport), dst, str(dport))
        else:
            return (dst, str(dport), src, str(sport))

    def _compute_rtt(self):
        """Compute RTT from SYN/SYN-ACK pairs"""
        # Group SYN and SYN-ACK packets by connection
        syns = {}  # (client, cport, server, sport) -> first SYN time
        for p in self.tcp_syn_packets:
            if not p["is_ack"]:  # pure SYN
                key = (p["src"], p["sport"], p["dst"], p["dport"])
                if key not in syns:
                    syns[key] = p["time"]
        # Match SYN-ACK
        for p in self.tcp_syn_packets:
            if p["is_ack"]:  # SYN-ACK
                # SYN-ACK goes from server to client, so reverse
                key = (p["dst"], p["dport"], p["src"], p["sport"])
                if key in syns:
                    rtt = p["time"] - syns[key]
                    if 0 <= rtt < 30:  # reasonable RTT range
                        self.rtt_samples.append({
                            "time": p["time"],
                            "src": p["src"],
                            "dst": p["dst"],
                            "rtt": rtt,
                        })

    def _compute_tcp_stream_analysis(self):
        """Compute retransmissions, duplicate ACKs and out-of-order packets from TCP streams"""
        # Group by stream: (src, sport, dst, dport)
        streams = defaultdict(list)
        for idx, pkt in enumerate(self.packets):
            if not pkt.haslayer(TCP) or not pkt.haslayer(IP):
                continue
            if not _match_filter(pkt, self.filter_expr):
                continue
            tcp = pkt[TCP]
            ip = pkt[IP]
            key = (ip.src, tcp.sport, ip.dst, tcp.dport)
            base_time = self.first_ts if self.first_ts else float(pkt.time)
            rel_time = float(pkt.time) - base_time
            streams[key].append({
                "frame": str(idx + 1),
                "time": rel_time,
                "src": ip.src,
                "dst": ip.dst,
                "sport": str(tcp.sport),
                "dport": str(tcp.dport),
                "seq": tcp.seq,
                "ack": tcp.ack,
                "len": len(tcp.payload),
                "flags": tcp.flags,
            })

        # Retransmission detection: the same seq appears multiple times within one stream
        self.retransmissions = []
        self.dup_acks = []
        self.out_of_order = []

        for key, pkts in streams.items():
            seen_seqs = {}  # seq -> (time, frame)
            seen_acks = {}  # ack -> count
            prev_seq = None
            for p in pkts:
                seq = p["seq"]
                # Retransmission: same seq seen before with data
                if p["len"] > 0 and seq in seen_seqs:
                    self.retransmissions.append({
                        "frame": p["frame"],
                        "time": p["time"],
                        "src": p["src"],
                        "dst": p["dst"],
                        "sport": p["sport"],
                        "dport": p["dport"],
                        "seq": str(seq),
                        "len": p["len"],
                    })
                if p["len"] > 0:
                    seen_seqs[seq] = (p["time"], p["frame"])

                # Duplicate ACK: same ACK value seen 2+ times
                ack = p["ack"]
                if ack in seen_acks:
                    seen_acks[ack] += 1
                    if seen_acks[ack] >= 2:
                        self.dup_acks.append({
                            "frame": p["frame"],
                            "time": p["time"],
                            "src": p["src"],
                            "dst": p["dst"],
                            "ack": str(ack),
                        })
                else:
                    seen_acks[ack] = 1

                # Out of order: seq decreased from previous
                if prev_seq is not None and p["len"] > 0 and seq < prev_seq:
                    self.out_of_order.append({
                        "frame": p["frame"],
                        "time": p["time"],
                        "src": p["src"],
                        "dst": p["dst"],
                        "len": p["len"],
                    })
                if p["len"] > 0:
                    prev_seq = seq

    def get_capinfos(self):
        """Generate capinfos-style text"""
        duration = (self.last_ts - self.first_ts) if self.first_ts and self.last_ts else 0
        avg_pkt_size = safe_div(self.total_bytes, self.total_packets) if self.total_packets else 0
        byte_rate = safe_div(self.total_bytes, duration) if duration > 0 else 0
        bit_rate = byte_rate * 8
        lines = [
            f"File name: {self.pcap_file}",
            f"File encapsulation: EN10MB",
            f"Number of packets: {self.total_packets}",
            f"File size: {self.total_bytes} bytes",
            f"Capture duration: {duration:.6f} seconds",
            f"Data byte rate: {byte_rate:.2f} bytes/sec",
            f"Data bit rate: {bit_rate:.2f} bits/sec",
            f"Average packet size: {avg_pkt_size:.2f} bytes",
        ]
        return "\n".join(lines)

    def get_conversations_text(self):
        """Generate the TCP conversation overview text"""
        lines = []
        lines.append("=" * 100)
        lines.append(f"{'TCP Conversations':^100}")
        lines.append("=" * 100)
        lines.append(
            f"{'Filter:':<12} {self.filter_expr or '<none>'}"
        )
        lines.append(
            f"{'<---  Address A --->':<24} {'<---  Address B --->':<24} "
            f"{'Frames A->B':>12} {'Bytes A->B':>12} {'Frames B->A':>12} {'Bytes B->A':>12} {'Duration':>10}"
        )
        lines.append("-" * 100)

        sorted_convs = sorted(self.conversations.items(),
                              key=lambda x: x[1]["bytes_a_b"] + x[1]["bytes_b_a"],
                              reverse=True)
        for key, conv in sorted_convs:
            src_a, port_a, src_b, port_b = key
            addr_a = f"{src_a}:{port_a}"
            addr_b = f"{src_b}:{port_b}"
            dur = f"{conv['end'] - conv['start']:.6f}" if conv['start'] is not None and conv['end'] is not None else "0"
            lines.append(
                f"{addr_a:<24} {addr_b:<24} "
                f"{conv['frames_a_b']:>12} {conv['bytes_a_b']:>12} "
                f"{conv['frames_b_a']:>12} {conv['bytes_b_a']:>12} {dur:>10}"
            )
        lines.append("")
        return "\n".join(lines)

    def get_io_stat_text(self):
        """Generate the per-second throughput statistics text"""
        lines = []
        lines.append("===================================================================")
        lines.append("IO Statistics")
        lines.append("===================================================================")
        lines.append(f"{'Interval':<12} {'Packets':>10} {'Bytes':>12}")
        lines.append("-------------------------------------------------------------------")
        for sec in sorted(self.io_stat.keys()):
            data = self.io_stat[sec]
            lines.append(f"[{sec:.0f}-{sec+1:.0f}]     {data['packets']:>10} {data['bytes']:>12}")
        lines.append("===================================================================")
        return "\n".join(lines)

    def get_window_sizes(self, src_ip):
        """Get the window-size time series for the given source IP"""
        return self.window_sizes_by_src.get(src_ip, [])

    def get_per_second_throughput(self, src_ip):
        """Get the per-second throughput for the given source IP"""
        return dict(self.throughput_by_src.get(src_ip, {}))

    def get_tcp_flags_dist(self):
        """TCP flags distribution"""
        return dict(self.tcp_flags_dist)


# -- Placeholder marker; the original reserved sections are appended below --
def analyze_mtu_issues(pkt_sizes, icmp_frag_needed, tcp_mss_values, retransmissions):
    """Analyze MTU / large-packet black-hole issues"""
    analysis = {
        "icmp_frag_needed": icmp_frag_needed,
        "tcp_mss_values": tcp_mss_values,
        "size_distribution": {},
        "large_packet_ratio": 0.0,
        "suspicious_pattern": False,
        "diagnosis": [],
    }

    if not pkt_sizes:
        return None

    # Packet size distribution statistics
    total = len(pkt_sizes)
    buckets = {
        "<100": 0,
        "100-500": 0,
        "500-1000": 0,
        "1000-1400": 0,
        "1400-1500": 0,
        ">1500": 0,
    }
    for s in pkt_sizes:
        if s < 100:
            buckets["<100"] += 1
        elif s < 500:
            buckets["100-500"] += 1
        elif s < 1000:
            buckets["500-1000"] += 1
        elif s < 1400:
            buckets["1000-1400"] += 1
        elif s <= 1500:
            buckets["1400-1500"] += 1
        else:
            buckets[">1500"] += 1

    analysis["size_distribution"] = buckets

    # Large-packet ratio (>1400 bytes)
    large_packets = buckets[">1500"] + buckets["1400-1500"]
    analysis["large_packet_ratio"] = large_packets / total * 100 if total > 0 else 0

    # Detect suspicious patterns
    # Pattern 1: ICMP Fragmentation Needed messages present
    if icmp_frag_needed:
        analysis["suspicious_pattern"] = True
        mtus = [m["next_hop_mtu"] for m in icmp_frag_needed if m.get("next_hop_mtu")]
        if mtus:
            min_mtu = min(mtus)
            analysis["diagnosis"].append(
                f"ICMP Fragmentation Needed message detected; path MTU limited to {min_mtu} bytes"
            )
        else:
            analysis["diagnosis"].append(
                "ICMP Fragmentation Needed message detected; a path MTU restriction exists"
            )

    # Pattern 2: very low large-packet ratio (<10%) with a large total packet count
    if total > 100 and analysis["large_packet_ratio"] < 10:
        analysis["suspicious_pattern"] = True
        analysis["diagnosis"].append(
            f"Large packets (>1400 bytes) account for only {analysis['large_packet_ratio']:.1f}%; "
            f"large packets may be dropped due to an MTU limit"
        )

    # Pattern 3: negotiated TCP MSS mismatches the actual packet sizes
    if tcp_mss_values and pkt_sizes:
        mss_vals = [m["mss"] for m in tcp_mss_values]
        if mss_vals:
            min_mss = min(mss_vals)
            max_pkt = max(pkt_sizes)
            # If the largest packet is close to MSS but retransmissions still occur, the path MTU may be smaller
            if max_pkt >= min_mss * 0.9 and retransmissions:
                large_retrans = [r for r in retransmissions if r.get("len") and r["len"] > 1000]
                if large_retrans:
                    analysis["suspicious_pattern"] = True
                    analysis["diagnosis"].append(
                        f"Negotiated TCP MSS is {min_mss} bytes but large packets are retransmitted; "
                        f"the path MTU may be smaller than the MSS value"
                    )

    # Pattern 4: >1500-byte packets present while no 1400-1500-byte packets (fragmentation issue)
    if buckets[">1500"] > 0 and buckets["1400-1500"] == 0:
        analysis["suspicious_pattern"] = True
        analysis["diagnosis"].append(
            ">1500-byte packets detected but no 1400-1500-byte packets; possible IP fragmentation issue"
        )

    return analysis


def generate_mtu_report(mtu_analysis, section_num=8):
    """Generate the MTU / large-packet black-hole analysis section"""
    if not mtu_analysis or not mtu_analysis.get("suspicious_pattern"):
        return ""

    lines = []
    lines.append(f"## {section_num}. MTU / Large-Packet Black-Hole Analysis")
    lines.append("")

    # Packet size distribution table
    if mtu_analysis.get("size_distribution"):
        lines.append("### Packet Size Distribution")
        lines.append("")
        lines.append("| Packet Size Range | Count | Ratio |")
        lines.append("|-----------|------|------|")
        total = sum(mtu_analysis["size_distribution"].values())
        for k, v in mtu_analysis["size_distribution"].items():
            pct = v / total * 100 if total > 0 else 0
            lines.append(f"| {k} | {v} | {pct:.1f}% |")
        lines.append("")

    # Negotiated TCP MSS values
    if mtu_analysis.get("tcp_mss_values"):
        mss_vals = [m["mss"] for m in mtu_analysis["tcp_mss_values"]]
        if mss_vals:
            lines.append("### TCP MSS Negotiation")
            lines.append("")
            lines.append(f"- **MSS range**: {min(mss_vals)} ~ {max(mss_vals)} bytes")
            lines.append(f"- **Corresponding MTU**: {min(mss_vals) + 40} ~ {max(mss_vals) + 40} bytes (including 40-byte IP+TCP headers)")
            lines.append("")

    # ICMP Fragmentation Needed
    if mtu_analysis.get("icmp_frag_needed"):
        lines.append("### ICMP Fragmentation Needed Messages")
        lines.append("")
        lines.append("| Time | Source | Destination | Next-Hop MTU |")
        lines.append("|------|-----|------|----------|")
        for m in mtu_analysis["icmp_frag_needed"]:
            mtu_str = f"{m['next_hop_mtu']} bytes" if m.get("next_hop_mtu") else "unspecified"
            lines.append(f"| t={m['time']:.3f}s | {m['src']} | {m['dst']} | {mtu_str} |")
        lines.append("")

    # Diagnosis
    if mtu_analysis.get("diagnosis"):
        lines.append("### Diagnosis")
        lines.append("")
        for d in mtu_analysis["diagnosis"]:
            lines.append(f"> {d}")
        lines.append("")

        # Remediation recommendations
        lines.append("### Remediation Recommendations")
        lines.append("")
        lines.append("**1. Reduce the interface MTU**")
        lines.append("")
        lines.append("**Linux**:")
        lines.append("```bash")
        lines.append("# Temporary change (lost after reboot)")
        lines.append("sudo ip link set dev <interface> mtu 1400")
        lines.append("")
        lines.append("# Permanent change (edit the NIC configuration file)")
        lines.append("# /etc/sysconfig/network-scripts/ifcfg-<interface>, add:")
        lines.append("# MTU=1400")
        lines.append("```")
        lines.append("")
        lines.append("**Windows**:")
        lines.append("```powershell")
        lines.append("# Run as administrator")
        lines.append("netsh interface ipv4 set subinterface \"<interface>\" mtu=1400 store=persistent")
        lines.append("```")
        lines.append("")
        lines.append("**2. Adjust TCP MSS (alternative that does not change the MTU)**")
        lines.append("")
        lines.append("**Linux**:")
        lines.append("```bash")
        lines.append("# Force the MSS via iptables (suitable for NAT/VPN scenarios)")
        lines.append("sudo iptables -t mangle -A POSTROUTING -p tcp --tcp-flags SYN,RST SYN "
                     "-j TCPMSS --set-mss 1360")
        lines.append("```")
        lines.append("")
        lines.append("**Windows**:")
        lines.append("```powershell")
        lines.append("# Adjust via the registry (reboot required)")
        lines.append("# HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces\\<interface GUID>")
        lines.append("# New DWORD: MTU = 1400 (decimal)")
        lines.append("```")
        lines.append("")
        lines.append("**3. Special notes for VPN/IPsec scenarios**")
        lines.append("")
        lines.append("- IPsec tunnel encapsulation adds 50-80 bytes of overhead (ESP header + IV + padding + auth)")
        lines.append("- Recommended MTU on both VPN ends: **1400 bytes** or lower")
        lines.append("- For tunnel protocols such as GRE/L2TP, subtract the tunnel header overhead as well")
        lines.append("")

    return "\n".join(lines)


# --- DNS anomaly analysis ----------------------------------------------------------

def analyze_dns_issues(dns_records, duration):
    """Analyze DNS anomalies"""
    analysis = {
        "total_queries": 0,
        "total_responses": 0,
        "no_response_queries": [],
        "error_responses": [],
        "tcp_fallback": [],
        "slow_responses": [],
        "suspicious_pattern": False,
        "diagnosis": [],
    }

    if not dns_records:
        return None

    # Group queries and responses by DNS ID
    queries_by_id = defaultdict(list)
    responses_by_id = defaultdict(list)
    for r in dns_records:
        if r["is_response"]:
            responses_by_id[r["id"]].append(r)
        else:
            queries_by_id[r["id"]].append(r)
            analysis["total_queries"] += 1

    analysis["total_responses"] = sum(len(v) for v in responses_by_id.values())

    # RCODE mapping
    rcode_map = {
        "0": "NoError", "1": "FormError", "2": "ServFail",
        "3": "NXDomain", "4": "NotImp", "5": "Refused",
    }

    # Detect queries without a response (timeout)
    for qid, qs in queries_by_id.items():
        if qid not in responses_by_id:
            for q in qs:
                analysis["no_response_queries"].append(q)

    # Detect error responses
    for rid, rs in responses_by_id.items():
        for r in rs:
            if r["rcode"] and r["rcode"] != "0":
                r["rcode_name"] = rcode_map.get(r["rcode"], f"Code {r['rcode']}")
                analysis["error_responses"].append(r)

    # Detect DNS truncation (TCP fallback)
    for r in dns_records:
        if r.get("truncated"):
            analysis["tcp_fallback"].append(r)

    # Detect slow responses (query-to-first-response gap > 1 second)
    for qid, qs in queries_by_id.items():
        if qid in responses_by_id:
            first_query_time = min(q["time"] for q in qs)
            first_resp_time = min(r["time"] for r in responses_by_id[qid])
            delay = first_resp_time - first_query_time
            if delay > 1.0:
                analysis["slow_responses"].append({
                    "query_name": qs[0]["query_name"],
                    "delay": delay,
                    "query_time": first_query_time,
                })

    # Diagnosis
    if analysis["no_response_queries"]:
        analysis["suspicious_pattern"] = True
        names = set(q["query_name"] for q in analysis["no_response_queries"])
        analysis["diagnosis"].append(
            f"{len(analysis['no_response_queries'])} DNS queries received no response "
            f"(domains involved: {', '.join(list(names)[:5])}); "
            f"the DNS server may be unreachable or query packets may be dropped"
        )

    nxdomain = [r for r in analysis["error_responses"] if r["rcode"] == "3"]
    servfail = [r for r in analysis["error_responses"] if r["rcode"] == "2"]
    refused = [r for r in analysis["error_responses"] if r["rcode"] == "5"]

    if nxdomain:
        analysis["suspicious_pattern"] = True
        names = set(r["query_name"] for r in nxdomain)
        analysis["diagnosis"].append(
            f"{len(nxdomain)} NXDomain responses detected "
            f"(domains: {', '.join(list(names)[:5])}); the domain does not exist or DNS is misconfigured"
        )
    if servfail:
        analysis["suspicious_pattern"] = True
        analysis["diagnosis"].append(
            f"{len(servfail)} ServFail responses detected; the upstream DNS server is misbehaving"
        )
    if refused:
        analysis["suspicious_pattern"] = True
        analysis["diagnosis"].append(
            f"{len(refused)} Refused responses detected; the DNS server refuses the queries"
        )

    if analysis["tcp_fallback"]:
        analysis["suspicious_pattern"] = True
        analysis["diagnosis"].append(
            f"{len(analysis['tcp_fallback'])} DNS responses were truncated (Truncated flag set); "
            f"clients may fall back to TCP queries, increasing latency"
        )

    if analysis["slow_responses"]:
        analysis["suspicious_pattern"] = True
        max_delay = max(r["delay"] for r in analysis["slow_responses"])
        analysis["diagnosis"].append(
            f"{len(analysis['slow_responses'])} slow DNS responses detected "
            f"(slowest {max_delay:.1f}s); DNS resolution delay slows down connection establishment"
        )

    return analysis


def generate_dns_report(dns_analysis, section_num):
    """Generate the DNS anomaly analysis section"""
    if not dns_analysis or not dns_analysis.get("suspicious_pattern"):
        return ""

    lines = []
    lines.append(f"## {section_num}. DNS Anomaly Analysis")
    lines.append("")

    lines.append("### DNS Overview")
    lines.append("")
    lines.append(f"- **Total DNS queries**: {dns_analysis['total_queries']}")
    lines.append(f"- **Total DNS responses**: {dns_analysis['total_responses']}")
    lines.append("")

    # Queries without response
    if dns_analysis.get("no_response_queries"):
        lines.append("### DNS Queries Without Response (Timeout)")
        lines.append("")
        lines.append("| Time | Source | Destination | Query Name | Query Type |")
        lines.append("|------|-----|------|----------|----------|")
        for q in dns_analysis["no_response_queries"][:20]:
            lines.append(f"| t={q['time']:.3f}s | {q['src']} | {q['dst']} | {q['query_name']} | {q['query_type']} |")
        if len(dns_analysis["no_response_queries"]) > 20:
            lines.append(f"| ... | {len(dns_analysis['no_response_queries'])} in total, showing the first 20 only | | | |")
        lines.append("")

    # Error responses
    if dns_analysis.get("error_responses"):
        lines.append("### DNS Error Responses")
        lines.append("")
        lines.append("| Time | Source | Destination | Query Name | RCODE | Description |")
        lines.append("|------|-----|------|----------|--------|------|")
        for r in dns_analysis["error_responses"][:20]:
            lines.append(f"| t={r['time']:.3f}s | {r['src']} | {r['dst']} | {r['query_name']} | {r['rcode']} | {r['rcode_name']} |")
        if len(dns_analysis["error_responses"]) > 20:
            lines.append(f"| ... | {len(dns_analysis['error_responses'])} in total, showing the first 20 only | | | | |")
        lines.append("")

    # Slow responses
    if dns_analysis.get("slow_responses"):
        lines.append("### Slow DNS Responses (>1s)")
        lines.append("")
        lines.append("| Query Time | Domain | Delay |")
        lines.append("|----------|------|------|")
        for r in dns_analysis["slow_responses"][:10]:
            lines.append(f"| t={r['query_time']:.3f}s | {r['query_name']} | {r['delay']:.1f}s |")
        lines.append("")

    # Diagnosis
    if dns_analysis.get("diagnosis"):
        lines.append("### DNS Diagnosis")
        lines.append("")
        for d in dns_analysis["diagnosis"]:
            lines.append(f"> {d}")
        lines.append("")

    return "\n".join(lines)


# --- TLS handshake failure analysis --------------------------------------------------

def analyze_tls_issues(tls_records, duration):
    """Analyze TLS handshake issues"""
    analysis = {
        "total_records": 0,
        "client_hellos": [],
        "server_hellos": [],
        "alerts": [],
        "versions_seen": set(),
        "server_names": set(),
        "suspicious_pattern": False,
        "diagnosis": [],
    }

    if not tls_records:
        return None

    # TLS version mapping
    version_map = {
        "0x0300": "SSL 3.0", "0x0301": "TLS 1.0", "0x0302": "TLS 1.1",
        "0x0303": "TLS 1.2", "0x0304": "TLS 1.3", "0x0200": "SSL 2.0",
    }

    # TLS Alert description mapping
    alert_map = {
        "0": "close_notify", "10": "unexpected_message", "20": "bad_record_mac",
        "40": "handshake_failure", "42": "bad_certificate",
        "43": "unsupported_certificate", "44": "certificate_revoked",
        "45": "certificate_expired", "46": "certificate_unknown",
        "47": "illegal_parameter", "48": "unknown_ca", "49": "access_denied",
        "50": "decode_error", "51": "decrypt_error", "70": "protocol_version",
        "71": "insufficient_security", "80": "internal_error",
        "86": "inappropriate_fallback", "90": "no_application_protocol",
        "100": "unknown_psk_identity",
    }

    for r in tls_records:
        analysis["total_records"] += 1

        if r["version"] and r["version"] in version_map:
            analysis["versions_seen"].add(version_map[r["version"]])

        if r["server_name"]:
            analysis["server_names"].add(r["server_name"])

        # ClientHello
        if r["handshake_type"] == "1":
            analysis["client_hellos"].append(r)
        # ServerHello
        elif r["handshake_type"] == "2":
            analysis["server_hellos"].append(r)

        # Alert
        if r["alert_message"]:
            r["alert_name"] = alert_map.get(r["alert_message"], f"Unknown ({r['alert_message']})")
            analysis["alerts"].append(r)

    # Diagnosis
    # ClientHello present but no ServerHello
    if analysis["client_hellos"] and not analysis["server_hellos"]:
        analysis["suspicious_pattern"] = True
        analysis["diagnosis"].append(
            f"{len(analysis['client_hellos'])} ClientHello(s) detected but no ServerHello response; "
            f"the TLS handshake did not complete. Possible causes: network packet loss, server refusing the connection, or a middlebox blocking it"
        )

    # Alert analysis
    if analysis["alerts"]:
        analysis["suspicious_pattern"] = True
        alert_types = set(a["alert_name"] for a in analysis["alerts"])

        if "handshake_failure" in alert_types:
            analysis["diagnosis"].append(
                "TLS Alert detected: **handshake_failure**. "
                "Common causes: cipher suite mismatch, unsupported certificate type, or incompatible protocol version"
            )
        if "protocol_version" in alert_types:
            analysis["diagnosis"].append(
                "TLS Alert detected: **protocol_version**. "
                "Client and server TLS versions are incompatible (e.g. the client only supports TLS 1.0 but the server requires TLS 1.2+)"
            )
        if "certificate_expired" in alert_types:
            analysis["diagnosis"].append(
                "TLS Alert detected: **certificate_expired**. The server certificate has expired and must be renewed"
            )
        if "unknown_ca" in alert_types:
            analysis["diagnosis"].append(
                "TLS Alert detected: **unknown_ca**. The client does not trust the CA that issued the server certificate"
            )
        if "bad_certificate" in alert_types:
            analysis["diagnosis"].append(
                "TLS Alert detected: **bad_certificate**. The server certificate format or content is malformed"
            )
        if "certificate_revoked" in alert_types:
            analysis["diagnosis"].append(
                "TLS Alert detected: **certificate_revoked**. The server certificate has been revoked"
            )
        if "access_denied" in alert_types:
            analysis["diagnosis"].append(
                "TLS Alert detected: **access_denied**. Access denied"
            )
        if "internal_error" in alert_types:
            analysis["diagnosis"].append(
                "TLS Alert detected: **internal_error**. Server internal error"
            )

    # Outdated TLS versions
    if analysis["versions_seen"]:
        old_versions = [v for v in analysis["versions_seen"]
                        if v in ("SSL 2.0", "SSL 3.0", "TLS 1.0", "TLS 1.1")]
        if old_versions:
            analysis["suspicious_pattern"] = True
            analysis["diagnosis"].append(
                f"Outdated TLS version(s) in use: {', '.join(old_versions)}. "
                f"They have known security vulnerabilities; upgrading to TLS 1.2 or TLS 1.3 is recommended"
            )

    analysis["versions_seen"] = list(analysis["versions_seen"])
    analysis["server_names"] = list(analysis["server_names"])
    return analysis


def generate_tls_report(tls_analysis, section_num):
    """Generate the TLS handshake analysis section"""
    if not tls_analysis or not tls_analysis.get("suspicious_pattern"):
        return ""

    lines = []
    lines.append(f"## {section_num}. TLS/SSL Handshake Analysis")
    lines.append("")

    lines.append("### TLS Overview")
    lines.append("")
    lines.append(f"- **Total TLS records**: {tls_analysis['total_records']}")
    lines.append(f"- **ClientHello count**: {len(tls_analysis['client_hellos'])}")
    lines.append(f"- **ServerHello count**: {len(tls_analysis['server_hellos'])}")
    if tls_analysis.get("versions_seen"):
        lines.append(f"- **TLS versions detected**: {', '.join(tls_analysis['versions_seen'])}")
    if tls_analysis.get("server_names"):
        lines.append(f"- **SNI server names**: {', '.join(tls_analysis['server_names'])}")
    lines.append("")

    # Alert messages
    if tls_analysis.get("alerts"):
        lines.append("### TLS Alert Messages")
        lines.append("")
        lines.append("| Time | Source | Destination | Alert Type | Description |")
        lines.append("|------|-----|------|-----------|------|")
        for a in tls_analysis["alerts"][:20]:
            lines.append(f"| t={a['time']:.3f}s | {a['src']} | {a['dst']} | {a['alert_message']} | {a['alert_name']} |")
        lines.append("")

    # Diagnosis
    if tls_analysis.get("diagnosis"):
        lines.append("### TLS Diagnosis")
        lines.append("")
        for d in tls_analysis["diagnosis"]:
            lines.append(f"> {d}")
        lines.append("")

        # Remediation recommendations
        lines.append("### Remediation Recommendations")
        lines.append("")
        lines.append("- Verify that the TLS versions supported by the client and server are compatible (TLS 1.2+ recommended)")
        lines.append("- Verify that the cipher suite configurations match")
        lines.append("- Verify that the server certificate is valid, not expired, and issued by a trusted CA")
        lines.append("- For self-signed certificates, add a trust entry on the client side")
        lines.append("")

    return "\n".join(lines)


# --- TCP connection establishment failure analysis -----------------------------------

def analyze_tcp_connection(syn_packets, duration):
    """Analyze TCP connection establishment issues"""
    analysis = {
        "total_syn": 0,
        "total_syn_ack": 0,
        "failed_connections": [],
        "syn_retransmissions": [],
        "slow_handshakes": [],
        "suspicious_pattern": False,
        "diagnosis": [],
    }

    if not syn_packets:
        return None

    # Group by connection direction: (client_ip, client_port, server_ip, server_port)
    syns_by_conn = defaultdict(list)
    syn_acks_by_conn = defaultdict(list)

    for p in syn_packets:
        if p["is_ack"]:
            # SYN-ACK (from server to client)
            key = (p["dst"], p["dport"], p["src"], p["sport"])
            syn_acks_by_conn[key].append(p)
        else:
            # Pure SYN (from client to server)
            key = (p["src"], p["sport"], p["dst"], p["dport"])
            syns_by_conn[key].append(p)
            analysis["total_syn"] += 1

    analysis["total_syn_ack"] = sum(len(v) for v in syn_acks_by_conn.values())

    # Detect SYNs without a SYN-ACK (connection establishment failure)
    for key, ss in syns_by_conn.items():
        if key not in syn_acks_by_conn:
            analysis["failed_connections"].append({
                "src": ss[0]["src"],
                "dst": ss[0]["dst"],
                "sport": ss[0]["sport"],
                "dport": ss[0]["dport"],
                "time": ss[0]["time"],
                "syn_count": len(ss),
            })

    # Detect SYN retransmissions (multiple SYNs for the same connection)
    for key, ss in syns_by_conn.items():
        if len(ss) > 1:
            analysis["syn_retransmissions"].append({
                "src": ss[0]["src"],
                "dst": ss[0]["dst"],
                "sport": ss[0]["sport"],
                "dport": ss[0]["dport"],
                "count": len(ss),
                "first_time": ss[0]["time"],
                "last_time": ss[-1]["time"],
            })

    # Detect slow handshakes (SYN-to-SYN-ACK gap > 1 second)
    for key, ss in syns_by_conn.items():
        if key in syn_acks_by_conn:
            first_syn = ss[0]
            first_syn_ack = syn_acks_by_conn[key][0]
            delay = first_syn_ack["time"] - first_syn["time"]
            if delay > 1.0:
                analysis["slow_handshakes"].append({
                    "src": first_syn["src"],
                    "dst": first_syn["dst"],
                    "sport": first_syn["sport"],
                    "dport": first_syn["dport"],
                    "delay": delay,
                })

    # Diagnosis
    if analysis["failed_connections"]:
        analysis["suspicious_pattern"] = True
        analysis["diagnosis"].append(
            f"{len(analysis['failed_connections'])} TCP connection(s) failed to establish "
            f"(SYN without SYN-ACK response). Possible causes: target port not listening, firewall dropping the SYN, or network unreachable"
        )

    if analysis["syn_retransmissions"]:
        analysis["suspicious_pattern"] = True
        total_retrans = sum(r["count"] - 1 for r in analysis["syn_retransmissions"])
        analysis["diagnosis"].append(
            f"{len(analysis['syn_retransmissions'])} connection(s) show SYN retransmissions "
            f"({total_retrans} retransmissions in total); the initial SYN was lost or the response timed out"
        )

    if analysis["slow_handshakes"]:
        analysis["suspicious_pattern"] = True
        max_delay = max(h["delay"] for h in analysis["slow_handshakes"])
        analysis["diagnosis"].append(
            f"{len(analysis['slow_handshakes'])} TCP handshake(s) took longer than 1 second "
            f"(slowest {max_delay:.1f}s); possible network latency or slow server processing"
        )

    return analysis


def generate_tcp_conn_report(tcp_conn_analysis, section_num):
    """Generate the TCP connection establishment analysis section"""
    if not tcp_conn_analysis or not tcp_conn_analysis.get("suspicious_pattern"):
        return ""

    lines = []
    lines.append(f"## {section_num}. TCP Connection Establishment Analysis")
    lines.append("")

    lines.append("### Connection Establishment Overview")
    lines.append("")
    lines.append(f"- **Total SYN packets**: {tcp_conn_analysis['total_syn']}")
    lines.append(f"- **Total SYN-ACK packets**: {tcp_conn_analysis['total_syn_ack']}")
    lines.append(f"- **Failed connections**: {len(tcp_conn_analysis['failed_connections'])}")
    lines.append(f"- **Connections with SYN retransmissions**: {len(tcp_conn_analysis['syn_retransmissions'])}")
    lines.append("")

    # Failed connections
    if tcp_conn_analysis.get("failed_connections"):
        lines.append("### Failed Connections (SYN Without Response)")
        lines.append("")
        lines.append("| Time | Source | Destination | Dst Port | SYN Retransmissions |")
        lines.append("|------|-----|------|----------|-------------|")
        for f in tcp_conn_analysis["failed_connections"][:20]:
            lines.append(f"| t={f['time']:.3f}s | {f['src']} | {f['dst']} | {f['dport']} | {f['syn_count']} |")
        if len(tcp_conn_analysis["failed_connections"]) > 20:
            lines.append(f"| ... | {len(tcp_conn_analysis['failed_connections'])} in total, showing the first 20 only | | | |")
        lines.append("")

    # SYN retransmissions
    if tcp_conn_analysis.get("syn_retransmissions"):
        lines.append("### SYN Retransmission Details")
        lines.append("")
        lines.append("| Source | Destination | Dst Port | Retransmissions | First Time | Last Time |")
        lines.append("|-----|------|----------|----------|----------|----------|")
        for r in tcp_conn_analysis["syn_retransmissions"][:20]:
            lines.append(
                f"| {r['src']} | {r['dst']} | {r['dport']} | {r['count']} | "
                f"t={r['first_time']:.3f}s | t={r['last_time']:.3f}s |"
            )
        lines.append("")

    # Slow handshakes
    if tcp_conn_analysis.get("slow_handshakes"):
        lines.append("### Slow TCP Handshakes (>1s)")
        lines.append("")
        lines.append("| Source | Destination | Dst Port | Handshake Delay |")
        lines.append("|-----|------|----------|----------|")
        for h in tcp_conn_analysis["slow_handshakes"][:10]:
            lines.append(f"| {h['src']} | {h['dst']} | {h['dport']} | {h['delay']:.1f}s |")
        lines.append("")

    # Diagnosis
    if tcp_conn_analysis.get("diagnosis"):
        lines.append("### TCP Connection Diagnosis")
        lines.append("")
        for d in tcp_conn_analysis["diagnosis"]:
            lines.append(f"> {d}")
        lines.append("")

    return "\n".join(lines)


# --- ICMP error summary analysis -------------------------------------------------------

def analyze_icmp_errors(icmp_records, duration):
    """Analyze ICMP error messages"""
    analysis = {
        "total_icmp": 0,
        "echo_requests": 0,
        "echo_replies": 0,
        "unreachable": [],
        "time_exceeded": [],
        "redirects": [],
        "frag_needed": [],
        "other_errors": [],
        "suspicious_pattern": False,
        "diagnosis": [],
    }

    if not icmp_records:
        return None

    for r in icmp_records:
        analysis["total_icmp"] += 1

        if r["type"] == "0":
            analysis["echo_replies"] += 1
        elif r["type"] == "8":
            analysis["echo_requests"] += 1
        elif r["type"] == "3":
            analysis["unreachable"].append(r)
            if r["code"] == "4":
                analysis["frag_needed"].append(r)
        elif r["type"] == "11":
            analysis["time_exceeded"].append(r)
        elif r["type"] == "5":
            analysis["redirects"].append(r)
        else:
            analysis["other_errors"].append(r)

    # Diagnosis
    if analysis["unreachable"]:
        port_unreach = [r for r in analysis["unreachable"] if r["code"] == "3"]
        host_unreach = [r for r in analysis["unreachable"] if r["code"] == "1"]
        net_unreach = [r for r in analysis["unreachable"] if r["code"] == "0"]
        admin_prohibit = [r for r in analysis["unreachable"] if r["code"] in ("9", "10", "13")]

        if port_unreach:
            analysis["suspicious_pattern"] = True
            analysis["diagnosis"].append(
                f"{len(port_unreach)} Port Unreachable message(s) detected; "
                f"the target port is not listening or the service is not running"
            )
        if host_unreach:
            analysis["suspicious_pattern"] = True
            analysis["diagnosis"].append(
                f"{len(host_unreach)} Host Unreachable message(s) detected; "
                f"the target host is unreachable (routing issue or host down)"
            )
        if net_unreach:
            analysis["suspicious_pattern"] = True
            analysis["diagnosis"].append(
                f"{len(net_unreach)} Network Unreachable message(s) detected; the target network is unreachable"
            )
        if admin_prohibit:
            analysis["suspicious_pattern"] = True
            analysis["diagnosis"].append(
                f"{len(admin_prohibit)} Administratively Prohibited message(s) detected; "
                f"traffic is blocked by a firewall or ACL policy"
            )

    if analysis["time_exceeded"]:
        ttl_exceeded = [r for r in analysis["time_exceeded"] if r["code"] == "0"]
        if ttl_exceeded:
            analysis["suspicious_pattern"] = True
            analysis["diagnosis"].append(
                f"{len(ttl_exceeded)} TTL Exceeded message(s) detected; "
                f"possible routing loop or TTL set too low"
            )

    if analysis["redirects"]:
        analysis["suspicious_pattern"] = True
        analysis["diagnosis"].append(
            f"{len(analysis['redirects'])} ICMP Redirect message(s) detected; "
            f"the network path is being redirected by a router"
        )

    return analysis


def generate_icmp_report(icmp_analysis, section_num):
    """Generate the ICMP error summary section"""
    if not icmp_analysis or not icmp_analysis.get("suspicious_pattern"):
        return ""

    lines = []
    lines.append(f"## {section_num}. ICMP Error Message Summary")
    lines.append("")

    lines.append("### ICMP Overview")
    lines.append("")
    lines.append(f"- **Total ICMP messages**: {icmp_analysis['total_icmp']}")
    lines.append(f"- **Echo Request (ping)**: {icmp_analysis['echo_requests']}")
    lines.append(f"- **Echo Reply (pong)**: {icmp_analysis['echo_replies']}")
    lines.append(f"- **Destination Unreachable**: {len(icmp_analysis['unreachable'])}")
    lines.append(f"- **Time Exceeded**: {len(icmp_analysis['time_exceeded'])}")
    lines.append(f"- **Redirect**: {len(icmp_analysis['redirects'])}")
    lines.append("")

    # Error message details
    all_errors = icmp_analysis["unreachable"] + icmp_analysis["time_exceeded"] + icmp_analysis["redirects"]
    if all_errors:
        lines.append("### ICMP Error Message Details")
        lines.append("")
        lines.append("| Time | Source | Destination | Type | Description |")
        lines.append("|------|-----|------|------|------|")
        for r in all_errors[:30]:
            mtu_str = f" (next-hop MTU: {r['next_hop_mtu']})" if r.get("next_hop_mtu") else ""
            lines.append(f"| t={r['time']:.3f}s | {r['src']} | {r['dst']} | {r['type_name']} | {r['code_name']}{mtu_str} |")
        if len(all_errors) > 30:
            lines.append(f"| ... | {len(all_errors)} in total, showing the first 30 only | | | |")
        lines.append("")

    # Diagnosis
    if icmp_analysis.get("diagnosis"):
        lines.append("### ICMP Diagnosis")
        lines.append("")
        for d in icmp_analysis["diagnosis"]:
            lines.append(f"> {d}")
        lines.append("")

    return "\n".join(lines)


# --- TCP Zero Window / Keepalive analysis -----------------------------------------------

def analyze_zero_window_keepalive(zero_windows, keepalives, duration):
    """Analyze TCP zero window and Keepalive events"""
    analysis = {
        "zero_window_count": len(zero_windows),
        "zero_window_events": zero_windows,
        "zero_window_duration": 0.0,
        "keepalive_count": len(keepalives),
        "keepalive_probes": 0,
        "keepalive_acks": 0,
        "suspicious_pattern": False,
        "diagnosis": [],
    }

    # Zero window analysis
    if zero_windows:
        if len(zero_windows) >= 2:
            first_zw = zero_windows[0]["time"]
            last_zw = zero_windows[-1]["time"]
            analysis["zero_window_duration"] = last_zw - first_zw

        analysis["suspicious_pattern"] = True
        analysis["diagnosis"].append(
            f"{len(zero_windows)} TCP zero window event(s) detected; "
            f"the receiver buffer is full and the sender is paused, impacting the transfer rate"
        )

        if analysis["zero_window_duration"] > 5:
            analysis["diagnosis"].append(
                f"The zero window state lasted {analysis['zero_window_duration']:.1f}s; "
                f"the receiver application has not read data for a long time, indicating a processing bottleneck"
            )

    # Keepalive analysis
    if keepalives:
        probes = [k for k in keepalives if k["is_keepalive"]]
        acks = [k for k in keepalives if k["is_keepalive_ack"]]
        analysis["keepalive_probes"] = len(probes)
        analysis["keepalive_acks"] = len(acks)

        if probes:
            analysis["suspicious_pattern"] = True
            analysis["diagnosis"].append(
                f"{len(probes)} TCP Keepalive probe(s) detected; "
                f"the connection may be idle or suffer from a one-way traffic issue"
            )

    return analysis


def generate_zw_ka_report(zw_ka_analysis, section_num):
    """Generate the TCP Zero Window / Keepalive analysis section"""
    if not zw_ka_analysis or not zw_ka_analysis.get("suspicious_pattern"):
        return ""

    lines = []
    lines.append(f"## {section_num}. TCP Zero Window / Keepalive Analysis")
    lines.append("")

    lines.append("### Overview")
    lines.append("")
    lines.append(f"- **Zero window events**: {zw_ka_analysis['zero_window_count']}")
    if zw_ka_analysis["zero_window_count"] > 0:
        lines.append(f"- **Zero window duration**: {zw_ka_analysis['zero_window_duration']:.1f}s")
    lines.append(f"- **Keepalive probes**: {zw_ka_analysis['keepalive_probes']}")
    lines.append(f"- **Keepalive ACKs**: {zw_ka_analysis['keepalive_acks']}")
    lines.append("")

    # Zero window event details
    if zw_ka_analysis.get("zero_window_events"):
        lines.append("### Zero Window Event Details")
        lines.append("")
        lines.append("| Time | Source | Destination | Src Port | Dst Port |")
        lines.append("|------|-----|------|--------|----------|")
        for zw in zw_ka_analysis["zero_window_events"][:20]:
            lines.append(f"| t={zw['time']:.3f}s | {zw['src']} | {zw['dst']} | {zw['sport']} | {zw['dport']} |")
        if len(zw_ka_analysis["zero_window_events"]) > 20:
            lines.append(f"| ... | {len(zw_ka_analysis['zero_window_events'])} in total, showing the first 20 only | | | |")
        lines.append("")

    # Diagnosis
    if zw_ka_analysis.get("diagnosis"):
        lines.append("### Diagnosis")
        lines.append("")
        for d in zw_ka_analysis["diagnosis"]:
            lines.append(f"> {d}")
        lines.append("")

        # Remediation recommendations
        if zw_ka_analysis["zero_window_count"] > 0:
            lines.append("### Remediation Recommendations")
            lines.append("")
            lines.append("- Check the receiver application for processing bottlenecks (slow disk IO, slow DB queries, etc.)")
            lines.append("- Increase the receiver TCP buffer size:")
            lines.append("  - **Linux**: `sysctl -w net.core.rmem_max=16777216` and set `SO_RCVBUF` in the application")
            lines.append("  - **Windows**: adjust window scaling via the `Tcp1323Params` registry key")
            lines.append("- Optimize the application-layer data consumption speed to avoid buffer backlog")
            lines.append("")

    return "\n".join(lines)


# --- IPsec/IKE analysis logic ------------------------------------------------------------

def analyze_ike_negotiation(ike_packets, ike_proposals, duration):
    """Analyze IKE negotiation (supports both IKEv1 and IKEv2)"""
    if not ike_packets:
        return None

    # IKEv2 error notify type names (used for failure detection)
    ikev2_failure_types = {
        "NO-PROPOSAL-CHOSEN", "TS-UNACCEPTABLE", "INVALID_SYNTAX",
        "INVALID_MESSAGE_INFORMATIONAL", "FAILED-CP-REQUIRED",
        "INVALID-SELECTORS", "INVALID_PACKET_FIELDS",
        "AUTHENTICATION-FAILED", "INVALID-CERTIFICATE",
        "CERT-REVOKED", "CERT-NOT-YET-VALID", "CERT-EXPIRED",
        "UNSUPPORTED_CRITICAL_PAYLOAD",
    }
    # IKEv2 NAT-T detection notifies
    ikev2_nat_notifies = {"NAT-DETECTION-SOURCE-IP", "NAT-DETECTION-DESTINATION-IP"}

    analysis = {
        "total_packets": len(ike_packets),
        "sessions": {},
        "failures": [],
        "success": False,
        "retry_count": 0,
        "retry_interval": None,
        "proposals_sent": [],
        "notifications_received": [],
        "nat_t_detected": False,
        "dpd_detected": False,
        "version_mismatch": False,
        "ike_versions": set(),
        "is_ikev2": False,
        "diagnosis": [],
    }

    # Group sessions by Initiator SPI
    sessions = defaultdict(list)
    for pkt in ike_packets:
        spi = pkt["init_spi"]
        if spi:
            sessions[spi].append(pkt)

    analysis["sessions"] = {k: len(v) for k, v in sessions.items()}

    # Analyze each session
    for spi, pkts in sessions.items():
        requests = [p for p in pkts if p["resp_spi"] == "" or p["resp_spi"] == "0" * len(p["resp_spi"])]
        responses = [p for p in pkts if p["resp_spi"] and p["resp_spi"] != "0" * len(p["resp_spi"])]

        # Detect retries
        if len(requests) > 1:
            times = [p["time"] for p in requests if p["time"] is not None]
            if len(times) >= 2:
                intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
                avg_interval = sum(intervals) / len(intervals) if intervals else None
                analysis["retry_count"] = len(requests) - 1
                analysis["retry_interval"] = avg_interval

        # Detect notify types
        for p in pkts:
            if p["notify_type"]:
                analysis["notifications_received"].append({
                    "time": p["time"],
                    "type": p["notify_type"],
                    "src": p["src"],
                })
                # Common failure detection for IKEv1 & IKEv2
                if p["notify_type"] in ikev2_failure_types:
                    analysis["failures"].append({
                        "time": p["time"],
                        "type": p["notify_type"],
                        "src": p["src"],
                    })
                # NAT-T detection (IKEv2 NAT-DETECTION notifies)
                if p["notify_type"] in ikev2_nat_notifies:
                    analysis["nat_t_detected"] = True

        # Detect IKEv2 exchange types
        for p in pkts:
            ver = p.get("ike_version", "")
            if ver:
                analysis["ike_versions"].add(ver)
            exch = p.get("exchtype", "")
            if "IKEv2" in exch:
                analysis["is_ikev2"] = True

    # Analyze SA proposals
    for prop in ike_proposals:
        if prop.get("encryption") or prop.get("auth_method") or prop.get("integrity") or prop.get("prf"):
            analysis["proposals_sent"].append(prop)
        if prop.get("nat_t"):
            analysis["nat_t_detected"] = True
        if prop.get("dpd"):
            analysis["dpd_detected"] = True

    # Detect version mismatch
    versions = set()
    for prop in ike_proposals:
        if prop.get("ike_version"):
            versions.add(prop["ike_version"])
    # Also collect versions at the packet level
    for pkt in ike_packets:
        ver = pkt.get("ike_version", "")
        if ver:
            versions.add(ver)
    analysis["ike_versions"] = versions
    if len(versions) > 1:
        analysis["version_mismatch"] = True
        analysis["diagnosis"].append(f"IKE version mismatch: detected {', '.join(sorted(versions))}")

    # Determine whether the negotiation succeeded
    has_notify_failure = any(f["type"] in ikev2_failure_types for f in analysis["failures"])
    if has_notify_failure:
        analysis["success"] = False
        failure_types = list(set(f["type"] for f in analysis["failures"]))
        for ft in failure_types:
            if ft == "NO-PROPOSAL-CHOSEN":
                analysis["diagnosis"].append(
                    "IKE SA negotiation failed: the responder returned NO-PROPOSAL-CHOSEN, "
                    "meaning the responder does not support any algorithm combination proposed by the initiator."
                )
            elif ft == "TS-UNACCEPTABLE":
                analysis["diagnosis"].append(
                    "IKE negotiation failed: TS-UNACCEPTABLE, the Traffic Selector was not accepted by the peer."
                )
            elif ft == "AUTHENTICATION-FAILED":
                analysis["diagnosis"].append(
                    "IKE negotiation failed: AUTHENTICATION-FAILED, authentication failed. Check the pre-shared key or certificate configuration."
                )
            else:
                analysis["diagnosis"].append(f"IKE negotiation failed: {ft}")
    elif analysis["failures"]:
        analysis["success"] = False
        for f in analysis["failures"]:
            analysis["diagnosis"].append(f"IKE negotiation failed: {f['type']} (from {f['src']})")
    else:
        # No explicit failure notify; check whether a full negotiation completed
        # IKEv1 Main Mode: 6 packets, IKEv2 SA_INIT+AUTH: 4 packets
        min_packets = 4 if analysis["is_ikev2"] else 4
        if len(ike_packets) >= min_packets:
            analysis["success"] = True
            ver_label = "IKEv2" if analysis["is_ikev2"] else "IKE"
            analysis["diagnosis"].append(f"{ver_label} negotiation appears complete (no failure notify detected).")
        else:
            analysis["diagnosis"].append("IKE negotiation may be incomplete; only a few packets were observed.")

    # Retry behavior diagnosis
    if analysis["retry_count"] > 0:
        interval = analysis["retry_interval"]
        if interval:
            analysis["diagnosis"].append(
                f"The initiator retried {analysis['retry_count']} time(s) at roughly {interval:.1f}s intervals, "
                f"indicating the initiator kept trying but was consistently rejected."
            )

    # Convert sets to lists for later serialization
    analysis["ike_versions"] = sorted(analysis["ike_versions"])

    return analysis


def analyze_ike_proposals_detail(ike_proposals):
    """Detailed analysis of the algorithm suites in IKE SA Proposals"""
    if not ike_proposals:
        return None

    detail = {
        "proposals": [],
        "is_gmssl": False,  # whether GM (Chinese national crypto) algorithms are used
        "algorithms": {},
    }

    for prop in ike_proposals:
        entry = {
            "exchange_type": prop.get("exchange_type"),
            "ike_version": prop.get("ike_version"),
            "encryption": prop.get("encryption"),
            "hash": prop.get("hash"),
            "integrity": prop.get("integrity"),
            "prf": prop.get("prf"),
            "auth_method": prop.get("auth_method"),
            "dh_group": prop.get("dh_group"),
            "key_length": prop.get("key_length"),
            "life_duration": prop.get("life_duration"),
            "notify_type": prop.get("notify_type"),
            "nat_t": prop.get("nat_t"),
            "dpd": prop.get("dpd"),
        }
        detail["proposals"].append(entry)

        # Detect GM (Chinese national crypto) algorithms (all IKEv1 + IKEv2 fields)
        gm_keywords = ["SM2", "SM3", "SM4", "Digital Envelope", "GM (Chinese national crypto)"]
        for kw in gm_keywords:
            for field in ["encryption", "hash", "integrity", "prf", "auth_method"]:
                if prop.get(field) and kw in prop[field]:
                    detail["is_gmssl"] = True

        # Aggregate algorithms (including IKEv2 fields)
        for field in ["encryption", "hash", "integrity", "prf", "auth_method", "dh_group"]:
            if prop.get(field):
                detail["algorithms"].setdefault(field, set()).add(prop[field])

    # Convert sets to lists for serialization
    for k in detail["algorithms"]:
        detail["algorithms"][k] = list(detail["algorithms"][k])

    return detail


# --- Analysis logic ---------------------------------------------------------------------

def analyze_rtt(rtt_samples):
    """Analyze RTT statistics"""
    if not rtt_samples:
        return None
    rtts = sorted([s["rtt"] for s in rtt_samples])
    n = len(rtts)
    stats = {
        "count": n,
        "min_ms": rtts[0] * 1000,
        "max_ms": rtts[-1] * 1000,
        "avg_ms": sum(rtts) / n * 1000,
        "p50_ms": rtts[n // 2] * 1000,
        "p95_ms": rtts[int(n * 0.95)] * 1000 if n >= 20 else rtts[-1] * 1000,
        "p99_ms": rtts[int(n * 0.99)] * 1000 if n >= 100 else rtts[-1] * 1000,
    }
    # Detect RTT spikes
    spikes = []
    for i in range(1, len(rtt_samples)):
        prev = rtt_samples[i - 1]["rtt"]
        curr = rtt_samples[i]["rtt"]
        if curr > prev * 3 and curr > 0.01:  # more than 3x and absolute value >10ms
            spikes.append({
                "time": rtt_samples[i]["time"],
                "from_ms": prev * 1000,
                "to_ms": curr * 1000,
            })
    stats["spikes"] = spikes[:10]  # report at most 10
    return stats


def analyze_window(windows, label):
    """Analyze window variation"""
    if not windows:
        return None
    vals = [w for _, w in windows]
    analysis = {
        "min": min(vals),
        "max": max(vals),
        "first": vals[0],
        "last": vals[-1],
        "samples": len(vals),
    }
    # Detect sudden window drops (>50% drop with absolute value >1000)
    drops = []
    for i in range(1, len(windows)):
        prev_w = windows[i - 1][1]
        curr_w = windows[i][1]
        if prev_w > 1000 and curr_w < prev_w * 0.5:
            drops.append({
                "time": windows[i][0],
                "from": prev_w,
                "to": curr_w,
                "ratio": curr_w / prev_w,
            })
    analysis["drops"] = drops[:10]

    # Detect persistently small windows (<10000 lasting >2 seconds)
    low_periods = []
    in_low = False
    low_start = 0
    low_min = float("inf")
    for t, w in windows:
        if w < 10000 and not in_low:
            in_low = True
            low_start = t
            low_min = w
        elif w < 10000 and in_low:
            low_min = min(low_min, w)
        elif w >= 10000 and in_low:
            in_low = False
            if t - low_start > 2.0:
                low_periods.append({
                    "start": low_start,
                    "end": t,
                    "duration": t - low_start,
                    "min_window": low_min,
                })
            low_min = float("inf")
    if in_low:
        end_t = windows[-1][0]
        if end_t - low_start > 2.0:
            low_periods.append({
                "start": low_start,
                "end": end_t,
                "duration": end_t - low_start,
                "min_window": low_min,
            })
    analysis["low_periods"] = low_periods
    return analysis


def analyze_throughput(buckets, duration):
    """Analyze throughput"""
    if not buckets:
        return None
    total_bytes = sum(buckets.values())
    max_sec = max(buckets.keys())
    per_sec = {}
    for sec in sorted(buckets):
        per_sec[sec] = {
            "bytes": buckets[sec],
            "kbps": buckets[sec] * 8 / 1024,
        }
    vals = [b["kbps"] for b in per_sec.values()]
    analysis = {
        "total_bytes": total_bytes,
        "duration_s": duration,
        "avg_kbps": total_bytes * 8 / 1024 / duration if duration > 0 else 0,
        "max_kbps": max(vals) if vals else 0,
        "min_kbps": min(vals) if vals else 0,
        "per_second": per_sec,
    }
    # Detect throughput drops
    drops = []
    prev_kbps = None
    for sec in sorted(per_sec):
        curr = per_sec[sec]["kbps"]
        if prev_kbps is not None and curr < prev_kbps * 0.5 and prev_kbps > 100:
            drops.append({"second": sec, "from_kbps": prev_kbps, "to_kbps": curr})
        prev_kbps = curr
    analysis["drops"] = drops
    return analysis


def analyze_fin_rst(fin_rst_packets, duration):
    """Analyze FIN/RST"""
    fins = [p for p in fin_rst_packets if p["is_fin"]]
    rsts = [p for p in fin_rst_packets if p["is_rst"]]
    analysis = {"fins": fins, "rsts": rsts}

    # Determine whether FIN is normal
    fin_notes = []
    if len(fins) == 2:
        # Normal TCP connection teardown (four-way handshake)
        f1, f2 = fins[0], fins[1]
        if f1["src"] != f2["src"]:
            dt = (f2["time"] - f1["time"]) if f2["time"] > f1["time"] else (f1["time"] - f2["time"])
            if dt < 1.0:
                fin_notes.append(f"Normal TCP close: both ends completed teardown within {dt*1000:.0f}ms")
            else:
                fin_notes.append(f"Teardown interval {dt*1000:.0f}ms, slightly long but within the normal range")
        else:
            fin_notes.append("Anomaly: both FINs came from the same side; the other side may not have responded properly")
    elif len(fins) == 1:
        fin_notes.append("Only a single FIN observed; the peer may not have responded or the capture may be incomplete")
    elif len(fins) > 2:
        fin_notes.append(f"{len(fins)} FIN packets observed; possible anomalous retransmissions or repeated close attempts")

    # Determine whether RST is abnormal
    rst_notes = []
    for r in rsts:
        if r["len"] and r["len"] > 0:
            rst_notes.append(f"The RST packet carries a payload ({r['len']} bytes); possibly a forged RST injected by a middlebox")
        else:
            rst_notes.append(f"RST packet from {r['src']}:{r['sport']} -> {r['dst']}:{r['dport']}, a normal connection reset")

    # An RST appearing after FIN may be normal
    if rsts and fins:
        last_fin_time = max(f["time"] for f in fins)
        for r in rsts:
            if r["time"] > last_fin_time:
                rst_notes.append(f"RST appeared after FIN (t={r['time']:.3f}s); likely normal cleanup of a half-closed state")

    analysis["fin_notes"] = fin_notes
    analysis["rst_notes"] = rst_notes
    return analysis


def analyze_retransmissions(retrans, dup_acks, ooo, duration):
    """Analyze retransmissions"""
    analysis = {
        "retrans_count": len(retrans),
        "dup_ack_count": len(dup_acks),
        "ooo_count": len(ooo),
    }

    notes = []
    # Determine whether retransmissions are abnormal
    if len(retrans) == 0:
        notes.append("No retransmissions; the transfer is healthy")
    elif len(retrans) <= 3:
        notes.append(f"Only {len(retrans)} retransmission(s), within the normal range")
    else:
        # Compute the retransmission rate
        notes.append(f"{len(retrans)} retransmissions in total, needs attention")
        # Detect burst retransmissions (>5 within 1 second)
        if retrans:
            times = [r["time"] for r in retrans if r["time"] is not None]
            for i in range(len(times)):
                burst = [t for t in times if times[i] <= t < times[i] + 1.0]
                if len(burst) > 5:
                    notes.append(f"  Burst retransmissions: {len(burst)} retransmission(s) within 1s starting at t={times[i]:.3f}s")
                    break

    # Out-of-order analysis
    if len(ooo) > 0:
        notes.append(f"{len(ooo)} out-of-order packet(s) detected")

    # Duplicate ACK analysis
    if len(dup_acks) > 3:
        notes.append(f"{len(dup_acks)} duplicate ACKs detected; fast retransmission may be triggered")

    analysis["notes"] = notes
    return analysis


# --- Report generation --------------------------------------------------------------------

def generate_ike_report(ike_analysis, ike_proposals_detail, section_num=9):
    """Generate the IPsec/IKE negotiation analysis section (supports IKEv1 and IKEv2)"""
    if not ike_analysis:
        return ""

    lines = []
    lines.append(f"## {section_num}. IPsec/IKE Negotiation Analysis")
    lines.append("")

    # Basic information
    lines.append("### IKE Session Overview")
    lines.append("")
    # Show the IKE version
    ike_versions = ike_analysis.get("ike_versions", [])
    is_ikev2 = ike_analysis.get("is_ikev2", False)
    if ike_versions:
        ver_str = ", ".join(ike_versions)
        ver_label = f"IKEv2" if is_ikev2 else f"IKEv1" if all(v.startswith("1") for v in ike_versions) else ver_str
        lines.append(f"- **IKE version**: {ver_label} ({ver_str})")
    elif is_ikev2:
        lines.append(f"- **IKE version**: IKEv2")
    lines.append(f"- **Total IKE packets**: {ike_analysis['total_packets']}")
    lines.append(f"- **Negotiation result**: {'Success' if ike_analysis['success'] else 'Failed'}")
    lines.append(f"- **Retry count**: {ike_analysis['retry_count']}")
    if ike_analysis['retry_interval']:
        lines.append(f"- **Retry interval**: {ike_analysis['retry_interval']:.1f} s")
    lines.append(f"- **NAT-Traversal**: {'Detected' if ike_analysis['nat_t_detected'] else 'Not detected'}")
    lines.append(f"- **DPD (Dead Peer Detection)**: {'Detected' if ike_analysis['dpd_detected'] else 'Not detected'}")
    lines.append(f"- **IKE version consistency**: {'Mismatch' if ike_analysis['version_mismatch'] else 'Consistent'}")
    lines.append("")

    # SA Proposal details
    if ike_proposals_detail and ike_proposals_detail.get("proposals"):
        lines.append("### SA Proposal Algorithm Suites")
        lines.append("")
        lines.append("| Parameter | Value |")
        lines.append("|------|-----|")
        for prop in ike_proposals_detail["proposals"]:
            if prop.get("encryption"):
                lines.append(f"| Encryption | {prop['encryption']} |")
            if prop.get("key_length"):
                lines.append(f"| Key Length | {prop['key_length']} bit |")
            if prop.get("hash"):
                lines.append(f"| Hash | {prop['hash']} |")
            if prop.get("integrity"):
                lines.append(f"| Integrity | {prop['integrity']} |")
            if prop.get("prf"):
                lines.append(f"| PRF | {prop['prf']} |")
            if prop.get("auth_method"):
                lines.append(f"| Authentication | {prop['auth_method']} |")
            if prop.get("dh_group"):
                lines.append(f"| DH Group | {prop['dh_group']} |")
            if prop.get("life_duration"):
                lines.append(f"| SA Lifetime | {prop['life_duration']} s |")
            if prop.get("exchange_type"):
                lines.append(f"| Exchange Mode | {prop['exchange_type']} |")
            if prop.get("ike_version"):
                lines.append(f"| IKE Version | {prop['ike_version']} |")
            break  # only show details of the first proposal (usually identical each time)
        lines.append("")

        # GM (Chinese national crypto) marker
        if ike_proposals_detail.get("is_gmssl"):
            lines.append("> **Note**: GM (Chinese national crypto) algorithms detected (SM2/SM3/SM4); both endpoints must support the GM module.")
            lines.append("")

    # Failure notifications
    if ike_analysis["notifications_received"]:
        lines.append("### Notify Messages Received")
        lines.append("")
        for n in ike_analysis["notifications_received"]:
            lines.append(f"- t={n['time']:.3f}s: **{n['type']}** (from {n['src']})")
        lines.append("")

    # Retry timeline
    if ike_analysis["retry_count"] > 0:
        lines.append("### Negotiation Retry Timeline")
        lines.append("")
        lines.append("| No. | Time (relative) | Event |")
        lines.append("|------|-------------|------|")
        idx = 1
        for f in ike_analysis.get("failures", []):
            lines.append(f"| {idx} | t={f['time']:.3f}s | {f['type']} |")
            idx += 1
        lines.append("")

    # Diagnosis
    if ike_analysis["diagnosis"]:
        lines.append("### IKE Diagnosis")
        lines.append("")
        for d in ike_analysis["diagnosis"]:
            lines.append(f"> {d}")
        lines.append("")

    return "\n".join(lines)


def generate_report(pcap, args, capinfos, conversations, io_stat,
                    rtt_stats, client_win, server_win, throughput,
                    fin_rst, retrans_analysis, pkt_sizes, flags_dist,
                    ike_analysis=None, ike_proposals_detail=None,
                    mtu_analysis=None,
                    dns_analysis=None, tls_analysis=None,
                    tcp_conn_analysis=None, icmp_analysis=None,
                    zw_ka_analysis=None):
    """Generate the Markdown analysis report"""
    lines = []
    lines.append(f"# Packet Capture Analysis Report")
    lines.append(f"")
    lines.append(f"**File**: `{os.path.basename(pcap)}`")
    lines.append(f"**Analysis time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.src or args.dst or args.port:
        filt_parts = []
        if args.src: filt_parts.append(f"src={args.src}")
        if args.dst: filt_parts.append(f"dst={args.dst}")
        if args.port: filt_parts.append(f"port={args.port}")
        lines.append(f"**Filter**: {', '.join(filt_parts)}")
    lines.append("")

    # -- 1. Basic information --
    lines.append("## 1. Capture Basic Information")
    lines.append("")
    # Extracted from capinfos
    for line in capinfos.split("\n"):
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            if k in ["File name", "Number of packets", "Capture duration",
                     "Data byte rate", "Data bit rate", "Average packet size",
                     "File size", "File encapsulation"]:
                lines.append(f"- **{k}**: {v}")
    lines.append("")

    # -- 2. TCP conversation overview --
    lines.append("## 2. TCP Conversation Overview")
    lines.append("")
    lines.append("```")
    for line in conversations.strip().split("\n"):
        lines.append(line)
    lines.append("```")
    lines.append("")

    # -- 3. Transfer rate analysis --
    lines.append("## 3. Transfer Rate Analysis")
    lines.append("")
    if throughput:
        lines.append(f"- **Total transferred**: {throughput['total_bytes']:,} bytes ({throughput['total_bytes']/1024/1024:.2f} MB)")
        lines.append(f"- **Average rate**: {throughput['avg_kbps']:.1f} kbps")
        lines.append(f"- **Peak rate**: {throughput['max_kbps']:.1f} kbps")
        lines.append(f"- **Minimum rate**: {throughput['min_kbps']:.1f} kbps")
        lines.append(f"- **Capture duration**: {throughput['duration_s']:.1f} s")
        lines.append("")

        if throughput["drops"]:
            lines.append("### Throughput Drops")
            lines.append("")
            for d in throughput["drops"]:
                lines.append(f"- t={d['second']}s: {d['from_kbps']:.1f} -> {d['to_kbps']:.1f} kbps (drop of {(1-d['to_kbps']/d['from_kbps'])*100:.0f}%)")
            lines.append("")

        lines.append("### Per-Second Throughput")
        lines.append("")
        lines.append("```")
        for sec in sorted(throughput["per_second"]):
            d = throughput["per_second"][sec]
            bar = "#" * int(d["kbps"] / 50)
            lines.append(f"  t={sec:3d}s | {d['kbps']:8.1f} kbps | {bar}")
        lines.append("```")
        lines.append("")

        # Rate diagnosis
        lines.append("### Rate Diagnosis")
        lines.append("")
        if throughput["avg_kbps"] < 1000:
            lines.append("> **Rate is low** (<1Mbps); correlate with the window and RTT analysis to locate the cause.")
        elif throughput["avg_kbps"] < 10000:
            lines.append("> **Rate is moderate** (1-10Mbps); a window or RTT bottleneck may exist.")
        else:
            lines.append("> **Rate is normal**.")
        lines.append("")

    # -- 4. Window analysis --
    lines.append("## 4. Window Size Analysis")
    lines.append("")
    if client_win:
        lines.append(f"### Sender (Client) Window")
        lines.append(f"- Range: {client_win['min']:,} ~ {client_win['max']:,} bytes")
        lines.append(f"- Initial window: {client_win['first']:,}")
        lines.append(f"- Final window: {client_win['last']:,}")
        lines.append("")
        if client_win["drops"]:
            lines.append("**Sudden window drop events**:")
            lines.append("")
            for d in client_win["drops"]:
                lines.append(f"- t={d['time']:.3f}s: {d['from']:,} -> {d['to']:,} (dropped to {d['ratio']*100:.0f}%)")
            lines.append("")
        if client_win["low_periods"]:
            lines.append("**Persistently small window (<10KB, >2s)**:")
            lines.append("")
            for p in client_win["low_periods"]:
                lines.append(f"- t={p['start']:.3f}s ~ {p['end']:.3f}s (lasted {p['duration']:.1f}s), min window {p['min_window']:,} bytes")
            lines.append("")

    if server_win:
        lines.append(f"### Receiver (Server) Window")
        lines.append(f"- Range: {server_win['min']:,} ~ {server_win['max']:,} bytes")
        lines.append(f"- Initial window: {server_win['first']:,}")
        lines.append(f"- Final window: {server_win['last']:,}")
        lines.append("")
        if server_win["drops"]:
            lines.append("**Sudden window drop events**:")
            lines.append("")
            for d in server_win["drops"]:
                lines.append(f"- t={d['time']:.3f}s: {d['from']:,} -> {d['to']:,} (dropped to {d['ratio']*100:.0f}%)")
            lines.append("")

    # Window diagnosis
    lines.append("### Window Diagnosis")
    lines.append("")
    win_issues = []
    # Check whether the client window stays small
    client_low = (client_win and client_win["last"] < 10000 and client_win["last"] < client_win["first"] * 0.3)
    client_low_periods = (client_win and client_win.get("low_periods"))
    if client_low or client_low_periods:
        if client_low_periods:
            p = client_win["low_periods"][0]
            win_issues.append(
                f"**Client receive window persistently small** (starting at t={p['start']:.3f}s, lasting {p['duration']:.1f}s, "
                f"min window {p['min_window']:,} bytes, only "
                f"{client_win['last']/client_win['first']*100:.0f}% of the initial window). "
                f"This indicates the client application reads data slower than the network receives it, causing receive-buffer backlog; "
                f"TCP flow control limits the sender's rate. **This is the main cause of the low transfer rate**."
            )
        else:
            win_issues.append(
                f"**Client receive window persistently small** (final {client_win['last']:,} bytes, only "
                f"{client_win['last']/client_win['first']*100:.0f}% of the initial window). "
                f"This indicates the client application reads data slower than the network receives it, causing receive-buffer backlog; "
                f"TCP flow control limits the sender's rate. **This is the main cause of the low transfer rate**."
            )
    if server_win and server_win["min"] < 10000:
        win_issues.append(f"The server window is also small (min {server_win['min']:,} bytes); the server may also have a processing bottleneck.")
    if not win_issues:
        win_issues.append("Window sizes are normal; no flow-control bottleneck found.")
    for issue in win_issues:
        lines.append(f"> {issue}")
    lines.append("")

    # -- 5. RTT analysis --
    lines.append("## 5. RTT Analysis")
    lines.append("")
    if rtt_stats:
        lines.append(f"- **Samples**: {rtt_stats['count']}")
        lines.append(f"- **Min RTT**: {rtt_stats['min_ms']:.2f} ms")
        lines.append(f"- **Max RTT**: {rtt_stats['max_ms']:.2f} ms")
        lines.append(f"- **Avg RTT**: {rtt_stats['avg_ms']:.2f} ms")
        lines.append(f"- **P50 RTT**: {rtt_stats['p50_ms']:.2f} ms")
        lines.append(f"- **P95 RTT**: {rtt_stats['p95_ms']:.2f} ms")
        lines.append(f"- **P99 RTT**: {rtt_stats['p99_ms']:.2f} ms")
        lines.append("")
        if rtt_stats["spikes"]:
            lines.append("**RTT spike events**:")
            lines.append("")
            for s in rtt_stats["spikes"]:
                lines.append(f"- t={s['time']:.3f}s: {s['from_ms']:.2f}ms -> {s['to_ms']:.2f}ms")
            lines.append("")

        # RTT diagnosis
        lines.append("### RTT Diagnosis")
        lines.append("")
        if rtt_stats["avg_ms"] < 10:
            rtt_verdict = "RTT is very low (<10ms), same-datacenter level."
        elif rtt_stats["avg_ms"] < 50:
            rtt_verdict = "RTT is low (<50ms), cross-region but the latency is normal."
        elif rtt_stats["avg_ms"] < 200:
            rtt_verdict = "RTT is moderate (50-200ms); possibly a transoceanic or satellite link."
        else:
            rtt_verdict = "RTT is high (>200ms), high-latency link."
        lines.append(f"> {rtt_verdict}")

        jitter = rtt_stats["p99_ms"] - rtt_stats["p50_ms"]
        if jitter > 100:
            lines.append(f"> RTT jitter is large (P99-P50={jitter:.1f}ms); possible network congestion or route changes.")
        else:
            lines.append(f"> RTT is stable (P99-P50={jitter:.1f}ms); network jitter is normal.")
        lines.append("")
    else:
        lines.append("No RTT samples detected (SYN/SYN-ACK may be missing or the capture may be incomplete).")
        lines.append("")

    # -- 6. Retransmission analysis --
    lines.append("## 6. Retransmission and Out-of-Order Analysis")
    lines.append("")
    lines.append(f"- **Retransmitted packets**: {retrans_analysis['retrans_count']}")
    lines.append(f"- **Duplicate ACKs**: {retrans_analysis['dup_ack_count']}")
    lines.append(f"- **Out-of-order packets**: {retrans_analysis['ooo_count']}")
    lines.append("")
    if retrans_analysis["notes"]:
        for n in retrans_analysis["notes"]:
            lines.append(f"- {n}")
        lines.append("")

    # -- 7. FIN/RST analysis --
    lines.append("## 7. FIN/RST Analysis")
    lines.append("")
    lines.append(f"- **FIN packets**: {len(fin_rst['fins'])}")
    lines.append(f"- **RST packets**: {len(fin_rst['rsts'])}")
    lines.append("")
    if fin_rst["fin_notes"]:
        lines.append("**FIN analysis**:")
        lines.append("")
        for n in fin_rst["fin_notes"]:
            lines.append(f"- {n}")
        lines.append("")
    if fin_rst["rst_notes"]:
        lines.append("**RST analysis**:")
        lines.append("")
        for n in fin_rst["rst_notes"]:
            lines.append(f"- {n}")
        lines.append("")

    # RST anomaly check
    if not fin_rst["rsts"]:
        lines.append("> No RST packets; the connection was not abnormally interrupted.")
    else:
        abnormal_rst = [r for r in fin_rst["rsts"] if r["len"] and r["len"] > 0]
        if abnormal_rst:
            lines.append(f"> **Found {len(abnormal_rst)} RST packet(s) carrying payload**; possibly forged RSTs injected by a middlebox (firewall/IPS); investigate with priority.")
        else:
            lines.append("> All RST packets are standard empty-payload RSTs, normal connection resets.")
    lines.append("")

    # -- 8. Packet size distribution --
    lines.append("## 8. Packet Size Distribution")
    lines.append("")
    if pkt_sizes:
        buckets = {"<100": 0, "100-500": 0, "500-1000": 0, "1000-1500": 0, ">1500": 0}
        for s in pkt_sizes:
            if s < 100: buckets["<100"] += 1
            elif s < 500: buckets["100-500"] += 1
            elif s < 1000: buckets["500-1000"] += 1
            elif s <= 1500: buckets["1000-1500"] += 1
            else: buckets[">1500"] += 1
        total = len(pkt_sizes)
        lines.append("| Packet Size Range | Count | Ratio |")
        lines.append("|-----------|------|------|")
        for k, v in buckets.items():
            pct = v / total * 100 if total > 0 else 0
            lines.append(f"| {k} | {v} | {pct:.1f}% |")
        lines.append("")
        # MSS check
        large = buckets[">1500"] + buckets["1000-1500"]
        if large / total < 0.5 and total > 100:
            lines.append("> Large packets account for less than 50%; possible MSS negotiation issue or frequent small application-layer messages.")
        lines.append("")

    # -- Dynamic sections: DNS / TLS / TCP connection / ICMP / MTU / Zero Window / IKE --
    next_section = 9

    # DNS anomaly analysis
    has_dns_issue = dns_analysis and dns_analysis.get("suspicious_pattern")
    if has_dns_issue:
        dns_report = generate_dns_report(dns_analysis, section_num=next_section)
        if dns_report:
            lines.append(dns_report)
            next_section += 1

    # TLS handshake analysis
    has_tls_issue = tls_analysis and tls_analysis.get("suspicious_pattern")
    if has_tls_issue:
        tls_report = generate_tls_report(tls_analysis, section_num=next_section)
        if tls_report:
            lines.append(tls_report)
            next_section += 1

    # TCP connection establishment analysis
    has_tcp_conn_issue = tcp_conn_analysis and tcp_conn_analysis.get("suspicious_pattern")
    if has_tcp_conn_issue:
        tcp_conn_report = generate_tcp_conn_report(tcp_conn_analysis, section_num=next_section)
        if tcp_conn_report:
            lines.append(tcp_conn_report)
            next_section += 1

    # ICMP error summary analysis
    has_icmp_issue = icmp_analysis and icmp_analysis.get("suspicious_pattern")
    if has_icmp_issue:
        icmp_report = generate_icmp_report(icmp_analysis, section_num=next_section)
        if icmp_report:
            lines.append(icmp_report)
            next_section += 1

    # MTU / large-packet black-hole analysis
    has_mtu_issue = mtu_analysis and mtu_analysis.get("suspicious_pattern")
    if has_mtu_issue:
        mtu_report = generate_mtu_report(mtu_analysis, section_num=next_section)
        if mtu_report:
            lines.append(mtu_report)
            next_section += 1

    # TCP Zero Window / Keepalive analysis
    has_zw_ka_issue = zw_ka_analysis and zw_ka_analysis.get("suspicious_pattern")
    if has_zw_ka_issue:
        zw_ka_report = generate_zw_ka_report(zw_ka_analysis, section_num=next_section)
        if zw_ka_report:
            lines.append(zw_ka_report)
            next_section += 1

    # IPsec/IKE negotiation analysis
    if ike_analysis:
        ike_report = generate_ike_report(ike_analysis, ike_proposals_detail, section_num=next_section)
        if ike_report:
            lines.append(ike_report)
            next_section += 1

    # -- Overall diagnosis --
    lines.append(f"## {next_section}. Overall Diagnosis")
    lines.append("")
    conclusions = []

    # Causes of low rate
    if throughput and throughput["avg_kbps"] < 1000:
        reasons = []
        if client_win and client_win["last"] < 10000:
            reasons.append(f"Client receive window persistently small ({client_win['last']:,} bytes); TCP flow control limits the send rate")
        if rtt_stats and rtt_stats["avg_ms"] > 100:
            reasons.append(f"RTT is high (avg {rtt_stats['avg_ms']:.0f}ms); the BDP is limited")
        if retrans_analysis["retrans_count"] > 10:
            reasons.append(f"Frequent retransmissions ({retrans_analysis['retrans_count']} times); effective throughput drops")
        if throughput["drops"]:
            reasons.append("Throughput drops detected; possible congestion or middlebox interference")
        if not reasons:
            reasons.append("No obvious network-layer bottleneck found; possibly limited by application-layer processing speed")
        conclusions.append(f"**Transfer rate is low** (avg {throughput['avg_kbps']:.0f}kbps), main reasons:")
        for i, r in enumerate(reasons, 1):
            conclusions.append(f"  {i}. {r}")

    # FIN/RST conclusions
    if fin_rst["rsts"]:
        abnormal = [r for r in fin_rst["rsts"] if r["len"] and r["len"] > 0]
        if abnormal:
            conclusions.append(f"**Abnormal RSTs present**: {len(abnormal)} RST(s) carry payload; suspected to be forged by a middlebox.")
        else:
            conclusions.append("All RSTs are normal connection resets.")
    else:
        conclusions.append("No RST; the connection was not abnormally interrupted.")

    # Retransmission conclusions
    if retrans_analysis["retrans_count"] > 10:
        conclusions.append(f"**Retransmissions are high**: {retrans_analysis['retrans_count']} retransmissions; investigate the link quality.")
    elif retrans_analysis["retrans_count"] > 0:
        conclusions.append(f"{retrans_analysis['retrans_count']} retransmission(s), within the normal range.")
    else:
        conclusions.append("No retransmissions; the link quality is good.")

    # DNS conclusions
    if has_dns_issue:
        no_resp = dns_analysis.get("no_response_queries", [])
        err_resp = dns_analysis.get("error_responses", [])
        slow = dns_analysis.get("slow_responses", [])
        if no_resp:
            conclusions.append(f"**DNS anomaly**: {len(no_resp)} query(ies) received no response; the DNS server may be unreachable.")
        if err_resp:
            rcodes = {}
            for e in err_resp:
                rc = e.get("rcode_name", "unknown")
                rcodes[rc] = rcodes.get(rc, 0) + 1
            rcode_str = ", ".join(f"{k} ({v}x)" for k, v in rcodes.items())
            conclusions.append(f"**DNS error responses**: {rcode_str}; check the domain configuration or the DNS server status.")
        if slow:
            conclusions.append(f"**Slow DNS responses**: {len(slow)} query(ies) took more than 1 second; may impact connection-setup latency.")

    # TLS conclusions
    if has_tls_issue:
        client_hellos = tls_analysis.get("client_hellos", [])
        server_hellos = tls_analysis.get("server_hellos", [])
        alerts = tls_analysis.get("alerts", [])
        outdated = [v for v in tls_analysis.get("versions_seen", [])
                    if v in ("SSL 2.0", "SSL 3.0", "TLS 1.0", "TLS 1.1")]
        if client_hellos and not server_hellos:
            conclusions.append(f"**TLS handshake failure**: {len(client_hellos)} ClientHello(s) received no ServerHello; the server may be unreachable or may not support TLS.")
        if alerts:
            alert_types = {}
            for a in alerts:
                at = a.get("alert_name", "unknown")
                alert_types[at] = alert_types.get(at, 0) + 1
            alert_str = ", ".join(f"{k} ({v}x)" for k, v in alert_types.items())
            conclusions.append(f"**TLS Alert**: {alert_str}; check the certificate configuration and TLS version compatibility.")
        if outdated:
            conclusions.append(f"**Outdated TLS versions**: {len(outdated)} outdated version(s) in use ({', '.join(outdated)}); upgrading to TLS 1.2+ is recommended.")

    # TCP connection establishment conclusions
    if has_tcp_conn_issue:
        failed = tcp_conn_analysis.get("failed_connections", [])
        slow_hs = tcp_conn_analysis.get("slow_handshakes", [])
        if failed:
            conclusions.append(f"**TCP connection establishment failure**: {len(failed)} SYN(s) received no SYN-ACK; the target port may be unreachable or blocked by a firewall.")
        if slow_hs:
            conclusions.append(f"**Slow TCP handshakes**: {len(slow_hs)} connection(s) had SYN -> SYN-ACK delay over 1 second; possible network congestion or middlebox delay.")

    # ICMP conclusions
    if has_icmp_issue:
        unreachable = len(icmp_analysis.get("unreachable", []))
        te = len(icmp_analysis.get("time_exceeded", []))
        redir = len(icmp_analysis.get("redirects", []))
        parts = []
        if unreachable > 0:
            parts.append(f"unreachable ({unreachable})")
        if te > 0:
            parts.append(f"time exceeded ({te})")
        if redir > 0:
            parts.append(f"redirect ({redir})")
        if parts:
            conclusions.append(f"**ICMP errors**: {'; '.join(parts)}; correlate with source/destination IPs to investigate routing or firewall policies.")

    # MTU / large-packet conclusions
    if has_mtu_issue:
        mtu_diags = mtu_analysis.get("diagnosis", [])
        if mtu_diags:
            conclusions.append(f"**MTU / large-packet black-hole risk**: {'; '.join(mtu_diags)}. Recommend reducing the interface MTU or adjusting the TCP MSS.")
        if mtu_analysis.get("icmp_frag_needed"):
            mtus = [m["next_hop_mtu"] for m in mtu_analysis["icmp_frag_needed"] if m.get("next_hop_mtu")]
            if mtus:
                conclusions.append(f"Path MTU limited to {min(mtus)} bytes (ICMP Fragmentation Needed); lower the interface MTU to this value or below.")

    # TCP Zero Window / Keepalive conclusions
    if has_zw_ka_issue:
        zw_count = zw_ka_analysis.get("zero_window_count", 0)
        ka_probes = zw_ka_analysis.get("keepalive_probes", 0)
        if zw_count > 0:
            total_dur = zw_ka_analysis.get("zero_window_duration", 0.0)
            conclusions.append(f"**TCP zero window**: {zw_count} zero window event(s), spanning {total_dur:.1f}s; receiver application processing is too slow. Increase the TCP receive buffer or speed up application-layer consumption.")
        if ka_probes > 0:
            conclusions.append(f"**TCP Keepalive**: {ka_probes} Keepalive probe(s) detected; the connection was idle for a long time, which is normal keepalive behavior.")

    for c in conclusions:
        lines.append(f"- {c}")
    lines.append("")

    return "\n".join(lines)


# --- Main flow (scapy implementation) ------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Deep packet capture analysis tool (pure Python/scapy implementation)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 pcap_analyze.py capture.pcap
  python3 pcap_analyze.py capture.pcap --src 10.0.0.1 --dst 10.0.0.2 --port 443
  python3 pcap_analyze.py capture.pcap --port 22 --output report.md
        """)
    parser.add_argument("pcap", help="Path to the pcap file")
    parser.add_argument("--src", help="Filter by source IP")
    parser.add_argument("--dst", help="Filter by destination IP")
    parser.add_argument("--port", help="Filter by port")
    parser.add_argument("--output", "-o", help="Output Markdown file path (defaults to stdout)")
    args = parser.parse_args()

    if not os.path.exists(args.pcap):
        print(f"[ERROR] File does not exist: {args.pcap}. Check the path and try again.", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(args.pcap):
        print(f"[ERROR] Not a regular file: {args.pcap}. Specify a pcap file.", file=sys.stderr)
        sys.exit(1)
    if not os.access(args.pcap, os.R_OK):
        print(f"[ERROR] File is not readable (permission denied): {args.pcap}. Fix the permissions and try again.", file=sys.stderr)
        sys.exit(1)

    # Build the filter expression
    filter_parts = []
    if args.src:
        filter_parts.append(f"ip.addr=={args.src}")
    if args.dst:
        filter_parts.append(f"ip.addr=={args.dst}")
    if args.port:
        filter_parts.append(f"tcp.port=={args.port}")
    filter_expr = " && ".join(filter_parts) if filter_parts else None
    if filter_expr:
        print(f"[INFO] Filter: {filter_expr}", file=sys.stderr)

    # Single-pass pcap processing
    proc = PcapProcessor(args.pcap, filter_expr)
    proc.process()

    duration = (proc.last_ts - proc.first_ts) if proc.first_ts and proc.last_ts else 30.0
    capinfos = proc.get_capinfos()
    conversations = proc.get_conversations_text()
    io_stat = proc.get_io_stat_text()

    # RTT
    print("[INFO] Analyzing RTT...", file=sys.stderr)
    rtt_stats = analyze_rtt(proc.rtt_samples)

    # Determine client/server
    src_ip = args.src
    dst_ip = args.dst
    if not src_ip and not dst_ip:
        # Auto-detect from conversations
        sorted_convs = sorted(proc.conversations.items(),
                              key=lambda x: x[1]["bytes_a_b"] + x[1]["bytes_b_a"],
                              reverse=True)
        for key, conv in sorted_convs:
            src_a, port_a, src_b, port_b = key
            if conv["bytes_a_b"] > conv["bytes_b_a"]:
                # A sends more -> A is server
                src_ip = src_b  # client
                dst_ip = src_a  # server
            else:
                src_ip = src_a  # client
                dst_ip = src_b  # server
            print(f"[INFO] Auto-detect: client={src_ip}, server={dst_ip}", file=sys.stderr)
            break

    # Window sizes
    print("[INFO] Analyzing window sizes...", file=sys.stderr)
    client_windows = proc.get_window_sizes(src_ip) if src_ip else []
    server_windows = proc.get_window_sizes(dst_ip) if dst_ip else []
    client_win = analyze_window(client_windows, "client")
    server_win = analyze_window(server_windows, "server")

    # Throughput
    print("[INFO] Analyzing throughput...", file=sys.stderr)
    throughput_buckets = proc.get_per_second_throughput(dst_ip) if dst_ip else {}
    throughput = analyze_throughput(throughput_buckets, duration)

    # FIN/RST
    print("[INFO] Analyzing FIN/RST...", file=sys.stderr)
    fin_rst = analyze_fin_rst(proc.fin_rst_packets, duration)

    # Retransmissions
    print("[INFO] Analyzing retransmissions...", file=sys.stderr)
    retrans_analysis = analyze_retransmissions(proc.retransmissions, proc.dup_acks, proc.out_of_order, duration)

    # TCP flags distribution
    flags_dist = proc.get_tcp_flags_dist()

    # -- IPsec/IKE analysis --
    ike_analysis = None
    ike_proposals_detail = None
    print("[INFO] Detecting IKE/IPsec traffic...", file=sys.stderr)
    if proc.ike_packets:
        print("[INFO] IKE traffic detected, starting IPsec/IKE negotiation analysis...", file=sys.stderr)
        ike_analysis = analyze_ike_negotiation(proc.ike_packets, proc.ike_raw_proposals, duration)
        ike_proposals_detail = analyze_ike_proposals_detail(proc.ike_raw_proposals)
    else:
        print("[INFO] No IKE traffic detected, skipping IPsec/IKE analysis.", file=sys.stderr)

    # -- MTU / large-packet black-hole analysis --
    print("[INFO] Analyzing MTU/large-packet issues...", file=sys.stderr)
    mtu_analysis = analyze_mtu_issues(proc.pkt_sizes, proc.icmp_frag_needed, proc.tcp_mss_values, proc.retransmissions)

    # -- DNS anomaly analysis --
    dns_analysis = None
    print("[INFO] Detecting DNS traffic...", file=sys.stderr)
    if proc.dns_records:
        print("[INFO] DNS traffic detected, starting DNS anomaly analysis...", file=sys.stderr)
        dns_analysis = analyze_dns_issues(proc.dns_records, duration)
    else:
        print("[INFO] No DNS traffic detected, skipping DNS analysis.", file=sys.stderr)

    # -- TLS handshake analysis --
    tls_analysis = None
    print("[INFO] Detecting TLS traffic...", file=sys.stderr)
    if proc.tls_records:
        print("[INFO] TLS traffic detected, starting TLS handshake analysis...", file=sys.stderr)
        tls_analysis = analyze_tls_issues(proc.tls_records, duration)
    else:
        print("[INFO] No TLS traffic detected, skipping TLS analysis.", file=sys.stderr)

    # -- TCP connection establishment analysis --
    print("[INFO] Analyzing TCP connection establishment...", file=sys.stderr)
    tcp_conn_analysis = analyze_tcp_connection(proc.tcp_syn_packets, duration)

    # -- ICMP error summary analysis --
    print("[INFO] Analyzing ICMP error messages...", file=sys.stderr)
    icmp_analysis = analyze_icmp_errors(proc.icmp_records, duration)

    # -- TCP Zero Window / Keepalive analysis --
    print("[INFO] Analyzing TCP zero window and Keepalive...", file=sys.stderr)
    zw_ka_analysis = analyze_zero_window_keepalive(proc.zero_windows, proc.keepalives, duration)

    print("[INFO] Generating report...", file=sys.stderr)
    report = generate_report(
        args.pcap, args, capinfos, conversations, io_stat,
        rtt_stats, client_win, server_win, throughput,
        fin_rst, retrans_analysis, proc.pkt_sizes, flags_dist,
        ike_analysis, ike_proposals_detail, mtu_analysis,
        dns_analysis, tls_analysis, tcp_conn_analysis,
        icmp_analysis, zw_ka_analysis
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[INFO] Report saved: {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
