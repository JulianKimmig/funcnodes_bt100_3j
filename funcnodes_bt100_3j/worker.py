from funcnodes import FuncNodesExternalWorker, instance_nodefunction
from .controller import BT100_3J
import time
from typing import Literal

from .ports import DEVICE_UPDATE_TIME, list_available_ports


class LongerBT1003JWorker(FuncNodesExternalWorker):
    NODECLASSID = "longerpump_BT100-3J"
    NODECLASSNAME = "Longerpump BT100-3J"

    def __init__(self, *args, **kwargs):
        self._controller = BT100_3J()
        super(LongerBT1003JWorker, self).__init__(*args, **kwargs)
        self._last_device_update = 0

    async def update_ports(self):
        available_devices = await list_available_ports()
        if (
            self._controller._connected
            and self._controller._port not in available_devices
        ):
            available_devices = [self._controller._port] + available_devices
        for node in self.set_port.nodes(self):
            node.inputs["port"].update_value_options(options=available_devices)
        self.set_port.nodeclass(self).input_port.update_value_options(
            options=available_devices
        )

    @instance_nodefunction()
    async def set_port(self, port: str):
        print(f"Connecting to port {port}")
        await self._controller.connect(port)
        self.update_state()

    @instance_nodefunction
    async def disconnect(self):
        await self._controller.disconnect()

    async def loop(self):
        if time.time() - self._last_device_update > DEVICE_UPDATE_TIME:
            self._last_device_update = time.time()
            await self.update_ports()

    def update_state(self):
        for node in self.set_state.nodes(self):
            node.inputs["rpm"].set_value(self._controller.rpm, does_trigger=False)
            node.inputs["clockwise"].set_value(
                self._controller.dir == self._controller.CLOCKWISE,
                does_trigger=False,
            )
            node.inputs["on"].set_value(
                self._controller.state == self._controller.START,
                does_trigger=False,
            )

        self.set_state.nodeclass(self).input_rpm.set_value(
            self._controller.rpm, does_trigger=False
        )
        self.set_state.nodeclass(self).input_clockwise.set_value(
            self._controller.dir == self._controller.CLOCKWISE,
            does_trigger=False,
        )
        self.set_state.nodeclass(self).input_on.set_value(
            self._controller.state == self._controller.START,
            does_trigger=False,
        )

    @instance_nodefunction()
    async def set_state(self, rpm: int = 50, clockwise: bool = True, on: bool = False):
        rpm = int(rpm)
        direction = (
            self._controller.CLOCKWISE
            if clockwise
            else self._controller.COUNTERCLOCKWISE
        )
        state = self._controller.START if on else self._controller.STOP
        await self._controller.set_state(rpm=rpm, dir=direction, state=state)
        self.update_state()

    @instance_nodefunction()
    async def pump_for(
        self, seconds: int, clockwise: bool = True, rpm: int = None
    ) -> bool:
        direction = (
            self._controller.CLOCKWISE
            if clockwise
            else self._controller.COUNTERCLOCKWISE
        )

        return await self._controller.pump_for(
            seconds=seconds,
            dir=direction,
            rpm=rpm,
        )
