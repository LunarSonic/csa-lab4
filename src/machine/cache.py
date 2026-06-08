import logging

logger = logging.getLogger(__name__)

CACHE_SIZE = 8
CACHE_HIT_TICKS = 1
CACHE_MISS_TICKS = 10


class CacheLine:
    def __init__(self, addr: int, value_: int) -> None:
        self.addr = addr
        self.value_ = value_

    def __repr__(self) -> str:
        return f"CacheLine(addr={self.addr}, value={self.value_})"


def read_word(memory: list[int], addr: int) -> int:
    return (memory[addr] << 24) | (memory[addr + 1] << 16) | (memory[addr + 2] << 8) | memory[addr + 3]


def write_word(memory: list[int], addr: int, value_: int) -> None:
    memory[addr] = (value_ >> 24) & 0xFF
    memory[addr + 1] = (value_ >> 16) & 0xFF
    memory[addr + 2] = (value_ >> 8) & 0xFF
    memory[addr + 3] = value_ & 0xFF


class Cache:
    def __init__(self) -> None:
        self.lines: dict[int, CacheLine] = {}
        self.hits = 0
        self.misses = 0

    def read(self, addr: int, memory: list[int]) -> tuple[int, int]:
        if addr in self.lines:
            self.hits += 1
            line = self.lines.pop(addr)
            self.lines[addr] = line
            logger.debug("CACHE HIT read addr=%d value=%d", addr, line.value_)
            return line.value_, CACHE_HIT_TICKS

        self.misses += 1
        value_ = read_word(memory, addr)
        logger.debug("CACHE MISS read addr=%d waiting %d ticks...", addr, CACHE_MISS_TICKS)
        self.load(addr, value_)
        return value_, CACHE_MISS_TICKS

    def write(self, addr: int, memory: list[int], value_: int) -> int:
        hit = addr in self.lines
        write_word(memory, addr, value_)
        if hit:
            self.lines[addr].value_ = value_
            self.hits += 1
            logger.debug("CACHE HIT write addr=%d value=%d", addr, value_)
            return CACHE_HIT_TICKS
        self.misses += 1
        logger.debug("CACHE MISS write addr=%d value=%d waiting 10 ticks", addr, value_)

        self.load(addr, value_)
        return CACHE_MISS_TICKS

    def load(self, addr: int, value_: int) -> None:
        if addr in self.lines:
            self.lines.pop(addr)
        elif len(self.lines) >= CACHE_SIZE:
            evicted_addr = next(iter(self.lines))
            del self.lines[evicted_addr]
            logger.debug("CACHE EVICT addr=%d", evicted_addr)
        self.lines[addr] = CacheLine(addr, value_)

    @property
    def total_accesses(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        if self.total_accesses == 0:
            return 0.0
        return self.hits / self.total_accesses

    def stats(self) -> str:
        return f"Cache: hits={self.hits} misses={self.misses} total={self.total_accesses} hit_rate={self.hit_rate:.1%}"

    def __repr__(self) -> str:
        return f"Cache(lines={list(self.lines.values())})"
