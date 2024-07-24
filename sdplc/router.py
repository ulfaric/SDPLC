from fastapi import APIRouter
from typing import List
from .schemas import Node
from .sdplc import simPLC
from Akatosh.universe import Mundus

sim_plc_router = APIRouter()


@sim_plc_router.get("/time/scale", tags=["Sim PLC"])
def set_time_scale(scale: int):
    """
    set_time_scale Set the time scale of the simulated PLC.

    The time scale adjusts the speed of the simulation. The default time scale is 1. Any value greater than 1 will speed up the simulation. Any value less than 1 will slow down the simulation.

    Args:
        scale (int): the time scale to set.
    """
    Mundus._time_scale = scale
    return {"details": f"Time scale set to {scale}."}


@sim_plc_router.get("/variables", response_model=List[Node], tags=["Sim PLC"])
def get_variables():
    """
    get_variables Get the list of variables in the simulated PLC.

    Get the list of variables in the simulated PLC. Note that there is no database to store the variables, so the variables are created and stored in memory. The value of variables are not persistent and will be reset when the server is restarted.

    """
    return simPLC.nodes


@sim_plc_router.get("/variables/read", tags=["Sim PLC"])
async def read_variable(qualified_name: str):
    """
    read_variable Read the value of a variable in the simulated PLC.

    Read the value of a variable in the simulated PLC. The variable is identified by its qualified name.

    Args:
        qualified_name (str): the qualified name of the variable to read.

    Returns:
        int | float | bool: the value of the variable.
    """
    readings = await simPLC.read_variable(qualified_name=qualified_name)
    return readings


@sim_plc_router.post("/variables/write", tags=["Sim PLC"])
async def write_variable(qualified_name: str, value: int | float | bool):
    """
    write_variable Write a value to a variable in the simulated PLC.

    Write a value to a variable in the simulated PLC. The variable is identified by its qualified name.

    Args:
        qualified_name (str): the qualified name of the variable to write.
        value (int | float | bool): the value to write to the variable.

    Returns:
        int | float | bool: read and return the value of the variable after writing.
    """
    await simPLC.write_variable(qualified_name=qualified_name, value=value)
    return await simPLC.read_variable(qualified_name=qualified_name)


# OPC UA endpoints
@sim_plc_router.get("/opcua/namespaces", tags=["Sim OPC UA"])
async def get_opcua_namespaces():
    """
    get_opcua_namespaces Get the list of namespaces in the simulated OPC UA server.

    Get the list of namespaces in the simulated OPC UA server.

    Returns:
        List[str]: the list of namespaces.
    """
    namespaces = await simPLC.opcuaServer.server.get_namespace_array()
    return namespaces


@sim_plc_router.get("/opcua/nodes", tags=["Sim OPC UA"])
async def get_opcua_nodes():
    """
    get_opcua_nodes Get the list of nodes in the simulated OPC UA server.

    Get the list of nodes in the simulated OPC UA server by browse name.

    Returns:
        List[str]: return the list of browse names of the nodes.
    """
    return [
        await node.read_browse_name() for _, node in simPLC.opcuaServer.nodes.items()
    ]


@sim_plc_router.get("/opcua/nodes/{node_id}/variables", tags=["Sim OPC UA"])
async def get_opcua_node_variables(node_id: str):
    """
    get_opcua_node_variables Get the list of variables under a node in the simulated OPC UA server.

    Get the list of variables under a node in the simulated OPC UA server by node id.

    Args:
        node_id (str): the node id of the parent node.

    Returns:
        List[str]: return the list of browse names of the variables under the node.
    """
    node = simPLC.opcuaServer.nodes[node_id]
    variables = await node.get_children()
    return [await variable.read_browse_name() for variable in variables]


# Modbus endpoints
@sim_plc_router.get("/modbus/slaves", tags=["Sim Modbus"])
async def get_modbus_slaves():
    """
    get_modbus_slaves Get the list of slave ids in the simulated Modbus server.

    Get the list of slave ids in the simulated Modbus server.

    Returns:
        List[int]: the list of slave ids.
    """
    return simPLC.modbusServer.slaves.keys()


@sim_plc_router.get("/modbus/slaves/{slave_id}/coils", tags=["Sim Modbus"])
async def get_modbus_coils(slave_id: int):
    """
    get_modbus_coils Get the addresses of coils in a slave in the simulated Modbus server.

    Get the addresses of coils in a slave in the simulated Modbus server.

    Args:
        slave_id (int): the id of the slave.

    Returns:
        List[int]: the list of coil addresses.
    """
    coils = [coil.address for coil in simPLC.modbusServer.slaves[slave_id].coils]
    return coils


@sim_plc_router.get("/modbus/slaves/{slave_id}/discrete_inputs", tags=["Sim Modbus"])
async def get_modbus_discrete_inputs(slave_id: int):
    """
    get_modbus_discrete_inputs Get the addresses of discrete inputs in a slave in the simulated Modbus server.

    Get the addresses of discrete inputs in a slave in the simulated Modbus server.

    Args:
        slave_id (int): the id of the slave.

    Returns:
        List[int]: the list of discrete input addresses.
    """
    discrete_inputs = [
        discrete_input.address
        for discrete_input in simPLC.modbusServer.slaves[slave_id].discrete_inputs
    ]
    return discrete_inputs


@sim_plc_router.get("/modbus/slaves/{slave_id}/holding_registers", tags=["Sim Modbus"])
async def get_modbus_holding_registers(slave_id: int):
    """
    get_modbus_holding_registers Get the addresses of holding registers in a slave in the simulated Modbus server.

    Get the addresses of holding registers in a slave in the simulated Modbus server.

    Args:
        slave_id (int): the id of the slave.

    Returns:
        List[int]: the list of holding register addresses.
    """
    holding_registers = [
        holding_register.address
        for holding_register in simPLC.modbusServer.slaves[slave_id].holding_registers
    ]
    return holding_registers


@sim_plc_router.get("/modbus/slaves/{slave_id}/input_registers", tags=["Sim Modbus"])
async def get_modbus_input_registers(slave_id: int):
    """
    get_modbus_input_registers Get the addresses of input registers in a slave in the simulated Modbus server.

    Get the addresses of input registers in a slave in the simulated Modbus server.

    Args:
        slave_id (int): the id of the slave.

    Returns:
        List[int]: the list of input register addresses.
    """
    input_registers = [
        input_register.address
        for input_register in simPLC.modbusServer.slaves[slave_id].input_registers
    ]
    return input_registers
