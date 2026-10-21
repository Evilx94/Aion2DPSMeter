"""Bounded binary fields, authored from format specifications; provenance pending."""
class InvalidData(ValueError):pass
class Cursor:
    def __init__(self,data,position=0):
        self.data=memoryview(data);self.position=position
        if not 0<=position<=len(self.data):raise InvalidData('position outside input')
    @property
    def remaining(self):return len(self.data)-self.position
    def take(self,size):
        if size<0 or size>self.remaining:raise InvalidData('incomplete field')
        at=self.position;self.position+=size;return bytes(self.data[at:self.position])
    def uint(self,size):return int.from_bytes(self.take(size),'little')
    def variable(self):
        bits=[]
        for _ in range(5):
            byte=self.uint(1);bits.append(byte&127)
            if byte<128:
                value=sum(part*128**power for power,part in enumerate(bits))
                if value>4294967295:raise InvalidData('unsigned32 overflow')
                return value
        raise InvalidData('unterminated unsigned32')

def raw_lz4(block,size,limit=8*1024*1024):
    if not 0<=size<=limit:raise InvalidData('output limit')
    source=Cursor(block);output=bytearray()
    def extended(short):
        if short!=15:return short
        total=15
        while True:
            added=source.uint(1);total+=added
            if total>limit:raise InvalidData('length limit')
            if added!=255:return total
    while source.remaining:
        token=source.uint(1)
        literal=extended(token>>4)
        if len(output)+literal>size:raise InvalidData('literal exceeds output')
        output.extend(source.take(literal))
        if not source.remaining:break
        distance=source.uint(2)
        if not 0<distance<=len(output):raise InvalidData('invalid backward distance')
        length=extended(token&15)+4
        if len(output)+length>size:raise InvalidData('match exceeds output')
        pattern=bytes(output[-distance:])
        repetitions,remainder=divmod(length,distance)
        output.extend(pattern*repetitions+pattern[:remainder])
    if len(output)!=size:raise InvalidData('output size mismatch')
    return bytes(output)
