from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class GateModel(BaseModel):
    name: str = Field(..., description="Name of the quantum gate (e.g., 'H', 'CX', 'RZ').")
    targets: List[int] = Field(..., description="List of target qubit indices.")
    controls: Optional[List[int]] = Field(None, description="List of control qubit indices (if any).")
    parameters: Optional[List[float | str]] = Field(None, description="List of parameters for the gate (e.g., rotation angles).")

class CircuitMetadata(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    # Add any other relevant metadata fields

class CircuitJSON(BaseModel):
    num_qubits: int = Field(..., description="Total number of qubits in the circuit.")
    gates: List[GateModel] = Field(..., description="List of gates in the circuit.")
    metadata: Optional[CircuitMetadata] = Field(None, description="Optional metadata for the circuit.")
    # Potentially add fields for classical registers, measurements, etc. later
    gate_counts: Optional[Dict[str, int]] = Field(None, description="Counts of each gate type.")
    depth: Optional[int] = Field(None, description="Depth of the circuit (longest path of gates).")

class QASMInput(BaseModel):
    qasm_string: str = Field(..., description="OpenQASM 2.0 or 3.0 string to be parsed.")

class OptimizationRequest(BaseModel):
    circuit: CircuitJSON
    passes: List[str] # e.g., ["gate_fusion", "depth_rebalance"]

class BenchmarkRequest(BaseModel):
    circuit: CircuitJSON
    simulator: str # e.g., "qiskit_aer", "pennylane_lightning"

class QASMOutput(BaseModel):
    qasm_string: str = Field(..., description="OpenQASM 2.0 string representing the circuit.")