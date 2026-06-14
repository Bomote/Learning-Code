import socket
import struct
import random


def build_dns_query(domain: str, record_type: int = 1) -> bytes:
    """Build a raw DNS query packet for an A record (type=1)."""

    # ---- Header section (12 bytes total) ----
    # Transaction ID: random 16-bit number so we can match the response
    # to this specific request (DNS is connectionless, so nothing else ties them together)
    transaction_id = random.randint(0, 65535)

    # Flags field (16 bits). 0x0100 in binary breaks down as:
    #   QR=0 (this is a query, not a response)
    #   Opcode=0000 (standard query)
    #   AA=0, TC=0
    #   RD=1 (recursion desired - ask the server to fully resolve this for us)
    #   Z=000, RCODE=0000
    flags = 0x0100

    qdcount = 1   # number of questions we're asking (just 1)
    ancount = 0   # number of answers (0 in a query - we're not providing answers)
    nscount = 0   # number of authority records (0 in a query)
    arcount = 0   # number of additional records (0 in a query)

    # Pack all six header fields as big-endian unsigned shorts (2 bytes each).
    # '>HHHHHH' = '>' big-endian, 'H' = unsigned short (16 bits), six of them = 12 bytes
    header = struct.pack(
        '>HHHHHH',
        transaction_id, flags, qdcount, ancount, nscount, arcount
    )

    # ---- Question section ----
    # DNS encodes domain names as a sequence of "labels", each prefixed by its length.
    # "example.com" becomes: 0x07 'example' 0x03 'com' 0x00
    # The 0x00 at the end is a zero-length label marking the end of the name.
    qname = b''
    for part in domain.split('.'):
        qname += struct.pack('B', len(part)) + part.encode('ascii')
    qname += b'\x00'  # terminating zero-length label

    qtype = record_type   # 1 = A record (IPv4 address)
    qclass = 1            # 1 = IN (Internet class - basically always 1)

    # QTYPE and QCLASS are each 2 bytes, big-endian
    question = qname + struct.pack('>HH', qtype, qclass)

    # Full packet = header + question
    # Also return transaction_id so we can verify the response matches
    return header + question, transaction_id


def parse_dns_response(data: bytes, transaction_id: int):
    """Parse a raw DNS response packet and extract any A record IP addresses."""

    # ---- Parse the 12-byte header (same layout as the query) ----
    (resp_id, flags, qdcount, ancount, nscount, arcount) = struct.unpack(
        '>HHHHHH', data[:12]
    )

    # Sanity check: make sure this response is actually answering OUR query.
    # Without this check, a spoofed or stray packet could be misread as our answer.
    if resp_id != transaction_id:
        raise ValueError("Transaction ID mismatch")

    # RCODE is the lowest 4 bits of the flags field. 0 = no error.
    # Common non-zero codes: 1=FormErr, 2=ServFail, 3=NXDOMAIN (domain doesn't exist)
    rcode = flags & 0x000F
    if rcode != 0:
        raise ValueError(f"DNS server returned error code: {rcode}")

    offset = 12  # start reading right after the header

    # ---- Skip over the question section ----
    # The response echoes back our question, so we need to skip past it
    # to get to the answer section. We don't need its contents.
    for _ in range(qdcount):
        offset = skip_name(data, offset)
        offset += 4  # skip QTYPE (2 bytes) + QCLASS (2 bytes)

    # ---- Parse each answer record ----
    ips = []
    for _ in range(ancount):
        # Each answer starts with a name (often a compressed pointer back
        # to the question's name, since it's the same domain)
        offset = skip_name(data, offset)

        # Fixed 10-byte record header:
        #   TYPE (2 bytes)    - what kind of record (1=A, 5=CNAME, etc.)
        #   CLASS (2 bytes)   - almost always 1 (IN)
        #   TTL (4 bytes)     - how long (in seconds) this record can be cached
        #   RDLENGTH (2 bytes)- how many bytes of actual data follow
        rtype, rclass, ttl, rdlength = struct.unpack(
            '>HHIH', data[offset:offset + 10]
        )
        offset += 10

        # RDATA - the actual record payload, RDLENGTH bytes long
        rdata = data[offset:offset + rdlength]
        offset += rdlength

        # We only care about A records (type 1) with a 4-byte IPv4 address.
        # Other types (CNAME, MX, TXT, etc.) are skipped - offset already
        # advanced past them, so the loop just continues.
        if rtype == 1 and rdlength == 4:
            # Each byte of rdata is one octet of the IP address
            ip = '.'.join(str(b) for b in rdata)
            ips.append((ip, ttl))

    return ips


def skip_name(data: bytes, offset: int) -> int:
    """
    Advance past a DNS name starting at `offset` and return the new offset.
    Handles DNS name compression, where a name can be replaced by a 2-byte
    pointer to an earlier occurrence of the same name elsewhere in the packet.
    """
    while True:
        length = data[offset]

        # A length of 0 marks the end of the name (the root label)
        if length == 0:
            return offset + 1

        # If the top two bits of this byte are both 1 (i.e. byte >= 0xC0),
        # this isn't a length - it's the start of a 2-byte compression pointer.
        # We don't need to follow the pointer (we're not reading the name's
        # value), just skip past these 2 bytes.
        if (length & 0xC0) == 0xC0:
            return offset + 2

        # Otherwise it's a normal label: 1 length byte + that many characters
        offset += 1 + length


def resolve(domain: str, dns_server: str = '8.8.8.8', port: int = 53):
    """Send a DNS query for `domain` to `dns_server` and return resolved IPs."""

    query, tid = build_dns_query(domain)

    # SOCK_DGRAM = UDP. Unlike TCP, there's no connect() - each sendto/recvfrom
    # is an independent packet, and the socket doesn't maintain a connection state.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)  # avoid hanging forever if the server doesn't respond

    try:
        sock.sendto(query, (dns_server, port))   # fire off the query packet
        response, _ = sock.recvfrom(512)         # wait for a reply (max 512 bytes, standard DNS UDP limit)
    finally:
        sock.close()

    return parse_dns_response(response, tid)


if __name__ == '__main__':
    domain = "example.com"
    results = resolve(domain, '8.8.8.8')

    print(f"DNS results for {domain}:")
    for ip, ttl in results:
        print(f"  {ip}  (TTL: {ttl}s)")