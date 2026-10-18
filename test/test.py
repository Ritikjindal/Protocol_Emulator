# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

# Must match CYCLES_PER_BIT in src/uart_tx.v
CYCLES_PER_BIT = 434
HALF_BIT = CYCLES_PER_BIT // 2  # 217


def tx(dut):
    """Current value of the TX pin (uo_out[0])."""
    return int(dut.uo_out.value[0])


def busy(dut):
    """Current value of the busy pin (uo_out[1])."""
    return int(dut.uo_out.value[1])


@cocotb.test()
async def test_uart_sends_A(dut):
    dut._log.info("Start")

    # 1. Clock: 20 ns period = 50 MHz, same as config.json
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)

    # Idle state after reset
    assert tx(dut) == 1, "TX should idle high after reset"
    assert busy(dut) == 0, "busy should be low after reset"

    # 2. Send: put the byte on the pins FIRST, then raise start
    byte_to_send = 0x41  # 'A'
    dut.ui_in.value = byte_to_send
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = 1  # start = uio_in[0]

    # 3a. Wait for the start bit's falling edge, one clock at a time.
    #     Give up after 20 cycles so a broken design fails instead of hanging.
    for _ in range(20):
        await ClockCycles(dut.clk, 1)
        if tx(dut) == 0:
            break
    else:
        assert False, "TX never went low: no start bit"

    # Handshake: the UART has accepted the byte, so release start
    assert busy(dut) == 1, "busy should be high once the frame starts"
    dut.uio_in.value = 0

    # 3b. Move to the middle of the start bit
    await ClockCycles(dut.clk, HALF_BIT)
    assert tx(dut) == 0, "start bit should still be 0 at its middle"

    # 3c. Sample the 8 data bits, one full bit apart, LSB first
    received = 0
    for i in range(8):
        await ClockCycles(dut.clk, CYCLES_PER_BIT)
        received |= tx(dut) << i

    # 3d. Middle of the stop bit
    await ClockCycles(dut.clk, CYCLES_PER_BIT)
    assert tx(dut) == 1, "stop bit should be 1"

    # 4. The byte itself
    dut._log.info(f"Received 0x{received:02X}")
    assert received == byte_to_send, (
        f"expected 0x{byte_to_send:02X}, got 0x{received:02X}"
    )

    # After the frame: busy drops, line returns to idle
    await ClockCycles(dut.clk, CYCLES_PER_BIT)
    assert busy(dut) == 0, "busy should drop after the frame"
    assert tx(dut) == 1, "TX should be idle high after the frame"