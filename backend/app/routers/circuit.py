from fastapi import APIRouter, HTTPException, Body
from ..models import QASMInput, CircuitJSON, GateModel, CircuitMetadata, OptimizationRequest, QASMOutput
from typing import List, Union, cast

# Qiskit for QASM parsing
from qiskit import qasm2, QuantumCircuit
from qiskit.circuit import Instruction, Qubit
from qiskit.circuit.parameterexpression import ParameterExpression

# Import conversion utilities and optimization passes
from ..utils.circuit_conversions import qiskit_circuit_to_json, circuit_json_to_qiskit
from ..services.optimization_passes import OPTIMIZATION_PASS_REGISTRY

router = APIRouter(
    prefix="/circuit",
    tags=["circuit"],
    responses={404: {"description": "Not found"}},
)

def _parse_qiskit_parameter(param):
    """Helper to parse Qiskit gate parameters."""
    if isinstance(param, ParameterExpression):
        # For symbolic parameters, convert to string.
        # For a more advanced system, you might want to evaluate them
        # or keep them as symbolic expressions.
        return str(param)
    elif isinstance(param, (float, int)):
        return param
    # Potentially handle other types if they appear
    return str(param) # Fallback

@router.post("/parse", response_model=CircuitJSON)
async def parse_qasm_to_json(qasm_input: QASMInput = Body(...)):
    """
    Parses an OpenQASM 2.0 string using Qiskit and converts it into an internal JSON representation.
    """
    if not qasm_input.qasm_string.strip().lower().startswith("openqasm 2.0;"):
        raise HTTPException(status_code=400, detail="Only OpenQASM 2.0 strings are supported by this endpoint currently. String must start with 'OPENQASM 2.0;'.")

    try:
        qc = qasm2.loads(qasm_input.qasm_string)
    except Exception as e:
        print(f"Qiskit QASM Parsing Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Qiskit QASM Parsing Error: {str(e)}")

    # Use the utility function to convert Qiskit QuantumCircuit to CircuitJSON
    return qiskit_circuit_to_json(qc)

@router.post("/optimize", response_model=CircuitJSON)
async def optimize_circuit(optimization_request: OptimizationRequest = Body(...)):
    """
    Applies specified optimization passes to the circuit.
    """
    current_circuit_json = optimization_request.circuit
    passes_to_apply = optimization_request.passes

    # For a more robust approach, convert to Qiskit, apply Qiskit transforms, then convert back.
    # Or, apply our custom JSON-based passes.
    
    optimized_circuit_json = current_circuit_json
    
    for pass_name in passes_to_apply:
        optimizer_func = OPTIMIZATION_PASS_REGISTRY.get(pass_name)
        if optimizer_func:
            optimized_circuit_json = optimizer_func(optimized_circuit_json)
            print(f"Applied optimization pass: {pass_name}")
        else:
            print(f"Warning: Optimization pass '{pass_name}' not found.")
            # Optionally raise HTTPException or just ignore

    # After custom JSON-based optimizations, stats (gate_counts, depth) are likely invalidated.
    # It's best to recalculate them by converting to a Qiskit circuit and back.
    if optimized_circuit_json.gate_counts is None or optimized_circuit_json.depth is None:
        try:
            # Convert to Qiskit to easily recalculate stats
            qiskit_qc = circuit_json_to_qiskit(optimized_circuit_json)
            # Convert back to JSON, which will include fresh stats
            final_optimized_json = qiskit_circuit_to_json(qiskit_qc)
            return final_optimized_json
        except Exception as e:
            print(f"Error during stats recalculation for optimized circuit: {e}")
            # Return the circuit with potentially stale/missing stats if recalculation fails
            return optimized_circuit_json
            
    return optimized_circuit_json

@router.post("/export/qasm", response_model=QASMOutput)
async def export_circuit_to_qasm(circuit_json: CircuitJSON = Body(...)):
    """
    Converts an internal CircuitJSON representation back to an OpenQASM 2.0 string.
    """
    qasm_lines = []
    qasm_lines.append("OPENQASM 2.0;")
    qasm_lines.append('include "qelib1.inc";') # Standard include for common gates

    if circuit_json.num_qubits > 0:
        qasm_lines.append(f"qreg q[{circuit_json.num_qubits}];")
    # Add classical register declarations here if your model supports them in the future
    # e.g., if circuit_json.num_clbits > 0:
    # qasm_lines.append(f"creg c[{circuit_json.num_clbits}];")

    for gate_model in circuit_json.gates:
        gate_str = gate_model.name
        
        # Handle parameters
        if gate_model.parameters:
            params_str = ",".join(map(str, gate_model.parameters))
            gate_str += f"({params_str})"
        
        gate_str += " "
        
        # Handle control and target qubits
        qubit_args = []
        if gate_model.controls:
            qubit_args.extend([f"q[{i}]" for i in gate_model.controls])
        
        # Targets must always be present
        qubit_args.extend([f"q[{i}]" for i in gate_model.targets])
        
        gate_str += ",".join(qubit_args)
        gate_str += ";"
        qasm_lines.append(gate_str)

    return QASMOutput(qasm_string="\n".join(qasm_lines))

# Add other circuit-related endpoints here later (e.g., /benchmark)