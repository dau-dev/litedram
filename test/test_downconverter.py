import unittest

from litex.gen import *

from litex.soc.interconnect.stream import *

from litedram.common import LiteDRAMWritePort, LiteDRAMReadPort
from litedram.frontend.adaptation import LiteDRAMPortConverter

from test.common import *


class DUT(Module):
    def __init__(self):
        # write port and converter
        self.write_user_port = LiteDRAMWritePort(aw=32, dw=64)
        self.write_crossbar_port = LiteDRAMWritePort(aw=32, dw=32)
        write_converter = LiteDRAMPortConverter(self.write_user_port,
                                                self.write_crossbar_port)
        self.submodules += write_converter

        # read port and converter
        self.read_user_port = LiteDRAMReadPort(aw=32, dw=64)
        self.read_crossbar_port = LiteDRAMReadPort(aw=32, dw=32)
        read_converter = LiteDRAMPortConverter(self.read_user_port,
                                               self.read_crossbar_port)
        self.submodules += read_converter

        # memory
        self.memory = DRAMMemory(32, 128)


write_data = [seed_to_data(i, nbits=64) for i in range(8)]
read_data = []


@passive
def read_generator(read_port):
    yield read_port.rdata.ready.eq(1)
    while True:
        if (yield read_port.rdata.valid):
            read_data.append((yield read_port.rdata.data))
        yield


def main_generator(write_port, read_port):
    # write
    for i in range(8):
        yield write_port.cmd.valid.eq(1)
        yield write_port.cmd.we.eq(1)
        yield write_port.cmd.adr.eq(i)
        yield write_port.wdata.valid.eq(1)
        yield write_port.wdata.data.eq(write_data[i])
        yield
        while (yield write_port.cmd.ready) == 0:
            yield
        while (yield write_port.wdata.ready) == 0:
            yield
        yield

    # read
    yield read_port.rdata.ready.eq(1)
    for i in range(8):
        yield read_port.cmd.valid.eq(1)
        yield read_port.cmd.we.eq(0)
        yield read_port.cmd.adr.eq(i)
        yield
        while (yield read_port.cmd.ready) == 0:
            yield
        yield read_port.cmd.valid.eq(0)
        yield

    # latency delay
    for i in range(32):
        yield


class TestDownConverter(unittest.TestCase):
    def test(self):
        dut = DUT()
        generators = {
            "sys" : [
                main_generator(dut.write_user_port, dut.read_user_port),
                read_generator(dut.read_user_port),
                dut.memory.write_generator(dut.write_crossbar_port),
                dut.memory.read_generator(dut.read_crossbar_port)
            ]
        }
        clocks = {"sys": 10}
        run_simulation(dut, generators, clocks, vcd_name="sim.vcd")
        self.assertEqual(write_data, read_data)