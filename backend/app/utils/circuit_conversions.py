from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Instruction, Qubit, Parameter
from qiskit.circuit.library.standard_gates import (
    HGate, XGate, YGate, ZGate, SGate, SdgGate, TGate, TdgGate, RXGate, RYGate, RZGate, UGate, CXGate, CZGate, SwapGate
    # Add other gates as needed
)


from ..models import CircuitJSON, GateModel, CircuitMetadata

# Mapping from our gate names to Qiskit gate classes
# This needs to be expanded for more comprehensive coverage
QISKIT_GATE_MAP = {
    "h": HGate,
    "x": XGate,
    "y": YGate,
    "z": ZGate,
    "s": SGate,
    "sdg": SdgGate,
    "t": TGate,
    "tdg": TdgGate,
    "rx": RXGate,
    "ry": RYGate,
    "rz": RZGate,
    "u": UGate, # Generic U gate (theta, phi, lambda)
    "cx": CXGate,
    "cnot": CXGate, # Alias for cx
    "cz": CZGate,
    "swap": SwapGate,
    # Add more mappings as your CircuitJSON supports more gates
}

def _parse_qiskit_parameter(param):
    """Helper to parse Qiskit gate parameters."""
    from qiskit.circuit.parameterexpression import ParameterExpression
    if isinstance(param, ParameterExpression):
        return str(param)
    elif isinstance(param, (float, int)):
        return param
    return str(param)

def qiskit_circuit_to_json(qc: QuantumCircuit) -> CircuitJSON:
    """
    Converts a Qiskit QuantumCircuit object to our CircuitJSON model.
    """
    gates = []
    for instruction_item in qc.data:
        instruction: Instruction = instruction_item.operation
        qargs_qiskit_qubits: list[Qubit] = instruction_item.qubits
        
        try:
            qargs_indices = [qc.find_bit(q).index for q in qargs_qiskit_qubits]
        except Exception as e:
            # Handle error or raise a custom exception
            print(f"Error finding qubit index during Qiskit to JSON conversion: {e}")
            # For simplicity, skip this instruction if error occurs
            continue 

        gate_name = instruction.name
        targets = []
        controls = []

        if hasattr(instruction, 'num_ctrl_qubits') and instruction.num_ctrl_qubits is not None and instruction.num_ctrl_qubits > 0:
            num_controls = instruction.num_ctrl_qubits
            if len(qargs_indices) >= num_controls:
                controls = qargs_indices[:num_controls]
                targets = qargs_indices[num_controls:]
            else:
                targets = qargs_indices # Fallback
        elif gate_name.lower() in ['cx', 'cnot'] and len(qargs_indices) == 2:
            controls = [qargs_indices[0]]
            targets = [qargs_indices[1]]
        elif gate_name.lower() in ['ccx', 'toffoli'] and len(qargs_indices) == 3:
            controls = [qargs_indices[0], qargs_indices[1]]
            targets = [qargs_indices[2]]
        else:
            targets = qargs_indices

        parameters = [_parse_qiskit_parameter(p) for p in instruction.params]

        gates.append(GateModel(
            name=gate_name,
            targets=targets,
            controls=controls if controls else None,
            parameters=parameters if parameters else None
        ))
    
    gate_counts_qiskit = qc.count_ops()
    calculated_gate_counts = {name: count for name, count in gate_counts_qiskit.items()}
    calculated_depth = qc.depth()
    
    metadata = CircuitMetadata(name=f"Converted Qiskit Circuit ({qc.name if qc.name else 'Untitled'})")

    return CircuitJSON(
        num_qubits=qc.num_qubits,
        gates=gates,
        metadata=metadata,
        gate_counts=calculated_gate_counts,
        depth=calculated_depth
    )

def circuit_json_to_qiskit(circuit_json: CircuitJSON) -> QuantumCircuit:
    """
    Converts our CircuitJSON model to a Qiskit QuantumCircuit object.
    """
    qc = QuantumCircuit(circuit_json.num_qubits)
    if circuit_json.metadata and circuit_json.metadata.name:
        qc.name = circuit_json.metadata.name

    for gate_model in circuit_json.gates:
        gate_name_lower = gate_model.name.lower()
        qiskit_gate_class = QISKIT_GATE_MAP.get(gate_name_lower)

        if not qiskit_gate_class:
            print(f"Warning: Gate '{gate_model.name}' not found in QISKIT_GATE_MAP. Skipping.")
            continue

        params = gate_model.parameters if gate_model.parameters else []
        
        # Prepare qubit arguments for Qiskit
        # Qiskit expects control qubits first, then target qubits for controlled gates.
        # For standard gates, it's just the target qubits.
        qiskit_qargs = []
        if gate_model.controls:
            qiskit_qargs.extend(gate_model.controls)
        qiskit_qargs.extend(gate_model.targets)
        
        try:
            # Some gates like UGate take parameters directly, others might need them unpacked
            if gate_name_lower == 'u': # UGate(theta, phi, lambda)
                 gate_instance = qiskit_gate_class(params[0], params[1], params[2])
            elif params:
                gate_instance = qiskit_gate_class(*params)
            else:
                gate_instance = qiskit_gate_class()
            
            # Apply gate to the circuit
            # For controlled gates, Qiskit's base gates (like XGate) have a .control() method
            if gate_model.controls and not gate_name_lower.startswith('c'): # e.g. H, X, RX but with controls in our model
                num_controls = len(gate_model.controls)
                if hasattr(gate_instance, 'control'):
                    # This creates a ControlledGate instance
                    controlled_gate_instance = gate_instance.control(num_ctrl_qubits=num_controls)
                    qc.append(controlled_gate_instance, qiskit_qargs)
                else:
                    print(f"Warning: Gate '{gate_model.name}' has controls but its Qiskit class {qiskit_gate_class} might not support .control() easily. Appending as non-controlled.")
                    qc.append(gate_instance, gate_model.targets) # Fallback to targets only
            else: # Standard gates or gates like CXGate where control is inherent
                qc.append(gate_instance, qiskit_qargs)

        except Exception as e:
            print(f"Error applying gate {gate_model.name} to Qiskit circuit: {e}. Qargs: {qiskit_qargs}, Params: {params}")
            import traceback
            traceback.print_exc()
            continue
            
    return qc