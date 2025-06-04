from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any

from app.models import (
    CircuitJSON,
    PennylaneScriptOutput, # Ensure this is imported
    QASMInput,
    OptimizationRequest,
    QASMOutput
)

from qiskit.qasm2 import loads as qiskit_loads_qasm2
from app.services.optimization_passes import OPTIMIZATION_PASS_REGISTRY

from app.utils.circuit_conversions import (
    qiskit_circuit_to_json,
    circuit_json_to_qiskit,
    circuit_json_to_cirq,
    cirq_circuit_to_json,
    circuit_json_to_pennylane_script # Ensure this is imported
)

router = APIRouter(
    prefix="/circuit",
    tags=["circuit"],
    responses={404: {"description": "Not found"}},
)

@router.post("/parse", response_model=CircuitJSON)
async def parse_qasm_to_json(qasm_input: QASMInput = Body(...)):
    """
    Parses an OpenQASM 2.0 string using Qiskit and converts it into an internal JSON representation.
    """
    if not qasm_input.qasm_string.strip().lower().startswith("openqasm 2.0;"):
        raise HTTPException(status_code=400, detail="Only OpenQASM 2.0 strings are supported by this endpoint currently. String must start with 'OPENQASM 2.0;'.")

    try:
        qc = qiskit_loads_qasm2(qasm_input.qasm_string)
    except Exception as e:
        print(f"Qiskit QASM Parsing Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Qiskit QASM Parsing Error: {str(e)}")
    return qiskit_circuit_to_json(qc)

@router.post("/optimize", response_model=CircuitJSON)
async def optimize_circuit(optimization_request: OptimizationRequest = Body(...)):
    """
    Applies specified optimization passes to the circuit.
    """
    current_circuit_json = optimization_request.circuit
    passes_to_apply = optimization_request.passes
    
    optimized_circuit_json = current_circuit_json
    
    for pass_name in passes_to_apply:
        optimizer_func = OPTIMIZATION_PASS_REGISTRY.get(pass_name)
        if optimizer_func:
            optimized_circuit_json = optimizer_func(optimized_circuit_json)
            print(f"Applied optimization pass: {pass_name}")
        else:
            print(f"Warning: Optimization pass '{pass_name}' not found.")

    if optimized_circuit_json.gate_counts is None or optimized_circuit_json.depth is None:
        try:
            qiskit_qc = circuit_json_to_qiskit(optimized_circuit_json)
            final_optimized_json = qiskit_circuit_to_json(qiskit_qc)
            return final_optimized_json
        except Exception as e:
            print(f"Error during stats recalculation for optimized circuit: {e}")
            return optimized_circuit_json
            
    return optimized_circuit_json

@router.post("/export/qasm", response_model=QASMOutput)
async def export_circuit_to_qasm(circuit_json: CircuitJSON = Body(...)):
    """
    Converts an internal CircuitJSON representation back to an OpenQASM 2.0 string.
    """
    qasm_lines = []
    qasm_lines.append("OPENQASM 2.0;")
    qasm_lines.append('include "qelib1.inc";') 

    if circuit_json.num_qubits > 0:
        qasm_lines.append(f"qreg q[{circuit_json.num_qubits}];")

    for gate_model in circuit_json.gates:
        gate_str = gate_model.name
        
        if gate_model.parameters:
            params_str = ",".join(map(str, gate_model.parameters))
            gate_str += f"({params_str})"
        
        gate_str += " "
        
        qubit_args = []
        if gate_model.controls:
            qubit_args.extend([f"q[{i}]" for i in gate_model.controls])
        
        qubit_args.extend([f"q[{i}]" for i in gate_model.targets])
        
        gate_str += ",".join(qubit_args)
        gate_str += ";"
        qasm_lines.append(gate_str)

    return QASMOutput(qasm_string="\n".join(qasm_lines))


# New Endpoint for Pennylane Script Export
@router.post("/export/pennylane_script", response_model=PennylaneScriptOutput, tags=["Export"])
async def export_circuit_to_pennylane_script_endpoint(
    circuit_json: CircuitJSON = Body(..., description="CircuitJSON representation of the quantum circuit")
):
    """
    Converts a CircuitJSON object to a Pennylane QNode Python script string.
    """
    if not circuit_json:
        raise HTTPException(status_code=400, detail="Input CircuitJSON is required.")
    try:
        script_str = circuit_json_to_pennylane_script(circuit_json)
        return PennylaneScriptOutput(script=script_str, message="Pennylane script generated successfully.")
    except ValueError as ve: # Catch specific errors if your function raises them
        # Log the exception ve if needed
        raise HTTPException(status_code=400, detail=f"Error generating Pennylane script: {str(ve)}")
    except Exception as e:
        # In a real app, log the exception `e` here
        print(f"Unexpected error generating Pennylane script: {e}") # Basic logging for now
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while generating the Pennylane script.")