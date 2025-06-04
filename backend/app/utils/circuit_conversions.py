from qiskit import QuantumCircuit, transpile
from qiskit.qasm2 import dumps as qiskit_dumps_qasm2
from qiskit.qasm2 import loads as qiskit_loads_qasm2
from qiskit.circuit import Parameter as QiskitParameter

import cirq
import numpy as np
import pennylane as qml
# from pennylane.ops.op_math import ControlledOperation # Commented out

from app.models import CircuitJSON, GateModel, CircuitMetadata

# --- Existing Qiskit Code ---
QISKIT_GATE_MAP = {
    "h": "h",
    "x": "x",
    "y": "y",
    "z": "z",
    "s": "s",
    "sdg": "sdg",
    "t": "t",
    "tdg": "tdg",
    "rx": "rx",
    "ry": "ry",
    "rz": "rz",
    "cx": "cx",
    "cnot": "cx", # Alias for cx
    "cz": "cz",
    "swap": "swap",
    "ccx": "ccx",
    "toffoli": "ccx", # Alias for ccx
    "id": "id",
    "u": "u", # Generic 3-parameter single-qubit gate
    "u3": "u", # Qiskit's u3 is often mapped to generic u
    "p": "p", # Phase gate
    # Add more mappings as needed
}
# ... (keep your existing qiskit_circuit_to_json and circuit_json_to_qiskit functions here) ...
def qiskit_circuit_to_json(qc: QuantumCircuit) -> CircuitJSON:
    """
    Converts a Qiskit QuantumCircuit object to our CircuitJSON model.
    """
    gates: list[GateModel] = []
    num_qubits = qc.num_qubits
    
    # Qiskit's qubit indexing is direct
    for instruction in qc.data:
        op = instruction.operation
        gate_name = op.name.lower()
        
        # Map Qiskit gate names to our canonical names if necessary
        # For now, assume direct mapping or use QISKIT_GATE_MAP if it were inverse
        
        targets = [qc.find_bit(q).index for q in instruction.qubits if qc.find_bit(q).index is not None]
        
        controls: list[int] | None = None
        # Qiskit specific way to identify controls for common gates
        if gate_name in ["cx", "cz", "ccx", "mcx", "mcz", "mcrx", "mcry", "mcrz"]: # Add other controlled gates
            num_controls = 0
            if hasattr(op, 'num_ctrl_qubits'):
                num_controls = op.num_ctrl_qubits
            elif gate_name == "cx": # CNOT
                num_controls = 1
            elif gate_name == "cz": # CZ
                num_controls = 1
            elif gate_name == "ccx": # Toffoli
                num_controls = 2
            
            if num_controls > 0 and len(targets) > num_controls:
                controls = targets[:num_controls]
                targets = targets[num_controls:]
        
        parameters: list[float | str] | None = None
        if op.params:
            parameters = []
            for p in op.params:
                if isinstance(p, (float, int)):
                    parameters.append(float(p))
                elif isinstance(p, QiskitParameter):
                     parameters.append(str(p)) # Store parameter expressions as strings
                else:
                    try:
                        parameters.append(float(p))
                    except (ValueError, TypeError):
                        print(f"Warning: Could not convert parameter {p} to float for gate {gate_name}. Storing as string.")
                        parameters.append(str(p))


        gates.append(GateModel(
            name=gate_name,
            targets=targets,
            controls=controls,
            parameters=parameters
        ))
        
    metadata = CircuitMetadata(name=qc.name if qc.name else "Converted Qiskit Circuit")
    
    # Calculate gate counts and depth
    # Qiskit's depth can be calculated, gate counts require iteration
    gate_counts_dict = {}
    for gate in gates:
        gate_counts_dict[gate.name] = gate_counts_dict.get(gate.name, 0) + 1
    
    try:
        depth = qc.depth()
    except Exception:
        depth = None # Fallback if depth calculation fails

    return CircuitJSON(
        num_qubits=num_qubits,
        gates=gates,
        metadata=metadata,
        gate_counts=gate_counts_dict if gate_counts_dict else None,
        depth=depth
    )

def circuit_json_to_qiskit(circuit_json: CircuitJSON) -> QuantumCircuit:
    """
    Converts our CircuitJSON model to a Qiskit QuantumCircuit object.
    """
    num_qubits = circuit_json.num_qubits
    qc = QuantumCircuit(num_qubits)
    
    if circuit_json.metadata and circuit_json.metadata.name:
        qc.name = circuit_json.metadata.name

    for gate_model in circuit_json.gates:
        gate_name_lower = gate_model.name.lower()
        qiskit_gate_name = QISKIT_GATE_MAP.get(gate_name_lower, gate_name_lower) # Fallback to original name

        params = gate_model.parameters if gate_model.parameters else []
        
        qubits_for_gate = []
        if gate_model.controls:
            qubits_for_gate.extend(gate_model.controls)
        qubits_for_gate.extend(gate_model.targets)

        try:
            gate_method = getattr(qc, qiskit_gate_name)
            
            # Qiskit's methods for gates usually take parameters first, then qubits
            if params:
                gate_method(*params, *qubits_for_gate)
            else:
                gate_method(*qubits_for_gate)
        except AttributeError:
            print(f"Warning: Gate '{qiskit_gate_name}' (from '{gate_model.name}') not found as a direct method on QuantumCircuit. Skipping.")
        except Exception as e:
            print(f"Error applying gate {gate_model.name} (as {qiskit_gate_name}) to Qiskit circuit: {e}")
            import traceback
            traceback.print_exc()
            
    return qc


# --- New Cirq Conversion Code ---

# Mapping from our gate names to Cirq gate objects/factories
# This needs to be comprehensive for the gates you support.
# Cirq often uses classes (e.g., cirq.H) or functions (e.g., cirq.rx)
CIRQT_GATE_MAP_TO_CIRQT = {
    "h": cirq.H,
    "x": cirq.X,
    "y": cirq.Y,
    "z": cirq.Z,
    "s": cirq.S,
    "t": cirq.T,
    "rx": cirq.rx,
    "ry": cirq.ry,
    "rz": cirq.rz,
    "cx": cirq.CNOT,
    "cnot": cirq.CNOT,
    "cz": cirq.CZ,
    "swap": cirq.SWAP,
    "id": cirq.I, # Identity gate
    # Parameterized gates might need special handling if they are not simple functions like rx, ry, rz
    # Example for a generic U gate (if you define one in your system)
    # "u": lambda p1, p2, p3: cirq.MatrixGate(QiskitCircuit().u(p1,p2,p3,0).data[0].operation.to_matrix()) # Hacky example
}

# Mapping from Cirq gate types/names back to our canonical names
# We will use isinstance checks in _get_cirq_gate_name instead of a direct type map here
# as specific gate types like cirq.HGate might not be top-level.
# This map can be used as a reference or for more complex scenarios if needed.
# For now, _get_cirq_gate_name will handle common cases.

# Old map that caused issues:
# CIRQT_GATE_MAP_FROM_CIRQT = {
#     cirq.HGate: "h", # Error: module 'cirq' has no attribute 'HGate'
#     cirq.XPowGate: "x",
#     cirq.YPowGate: "y",
#     cirq.ZPowGate: "z",
#     cirq.HPowGate: "h", # Note: cirq.H is HPowGate(exponent=1)
#     cirq.SGate: "s",   # cirq.S is ZPowGate(exponent=0.5)
#     cirq.TGate: "t",   # cirq.T is ZPowGate(exponent=0.25)
#     cirq.Rx: "rx",     # This is a function, not a type. type(cirq.rx(0.1)) is RxGate
#     cirq.Ry: "ry",     # type(cirq.ry(0.1)) is RyGate
#     cirq.Rz: "rz",     # type(cirq.rz(0.1)) is RzGate
#     cirq.CNotPowGate: "cx",
#     cirq.CZPowGate: "cz",
#     cirq.SwapPowGate: "swap",
#     cirq.IdentityGate: "id",
# }

def _get_cirq_gate_name(gate: cirq.Gate) -> str:
    """Helper to get a canonical name from a Cirq gate instance."""
    # Order of checks matters, more specific first.
    if isinstance(gate, cirq.ops.ControlledGate):
        # For controlled gates, get the name of the sub_gate and prefix with 'c'
        # This is a simplification; multi-control needs more sophisticated naming.
        sub_gate_name = _get_cirq_gate_name(gate.sub_gate)
        if gate.num_controls() == 1: # TODO: Handle num_controls() for different cirq versions if API changes
            return f"c{sub_gate_name}"
        return f"c{gate.num_controls()}_{sub_gate_name}" # e.g., c2_x for Toffoli if sub_gate is X

    if isinstance(gate, cirq.ops.HPowGate) and gate.exponent == 1: return "h"
    if isinstance(gate, cirq.ops.XPowGate) and gate.exponent == 1: return "x"
    if isinstance(gate, cirq.ops.YPowGate) and gate.exponent == 1: return "y"
    if isinstance(gate, cirq.ops.ZPowGate):
        if gate.exponent == 1: return "z"
        if gate.exponent == 0.5: return "s"
        if gate.exponent == -0.5: return "sdg" # Assuming you have 'sdg'
        if gate.exponent == 0.25: return "t"
        if gate.exponent == -0.25: return "tdg" # Assuming you have 'tdg'
        return f"z**{gate.exponent}" # General ZPowGate

    if isinstance(gate, cirq.ops.Rx): return "rx" # Rx is a class cirq.ops. συγκεκριμένα.Rx
    if isinstance(gate, cirq.ops.Ry): return "ry" # Ry is a class cirq.ops.Ry
    if isinstance(gate, cirq.ops.Rz): return "rz" # Rz is a class cirq.ops.Rz
    
    if isinstance(gate, cirq.ops.CNotPowGate) and gate.exponent == 1: return "cx"
    if isinstance(gate, cirq.ops.CZPowGate) and gate.exponent == 1: return "cz"
    if isinstance(gate, cirq.ops.SwapPowGate) and gate.exponent == 1: return "swap"
    if isinstance(gate, cirq.ops.IdentityGate): return "id"

    # Fallback name extraction (can be improved)
    name = str(gate).lower()
    if '(' in name: # Remove parameters part like in "H(q0)" -> "h"
        name = name.split('(')[0]
    
    # Further simplify common cirq names if they weren't caught by isinstance
    if name == "h": return "h"
    if name == "x": return "x"
    if name == "y": return "y"
    if name == "z": return "z"
    if name == "s": return "s"
    if name == "t": return "t"
    if name == "cnot": return "cx"
    if name == "cz": return "cz"
    if name == "swap": return "swap"
    if name == "i": return "id"

    return name if name else "unknown"


def circuit_json_to_cirq(circuit_json: CircuitJSON) -> cirq.Circuit:
    """
    Converts our CircuitJSON model to a Cirq Circuit object.
    """
    num_qubits = circuit_json.num_qubits
    qubits = cirq.LineQubit.range(num_qubits)
    circuit = cirq.Circuit()

    for gate_model in circuit_json.gates:
        gate_name_lower = gate_model.name.lower()
        cirq_gate_constructor = CIRQT_GATE_MAP_TO_CIRQT.get(gate_name_lower)

        if not cirq_gate_constructor:
            print(f"Warning: Gate '{gate_model.name}' not found in CIRQT_GATE_MAP_TO_CIRQT. Skipping.")
            continue

        try:
            target_qubits_indices = gate_model.targets
            cirq_target_qubits = [qubits[i] for i in target_qubits_indices]
            
            gate_instance: cirq.Gate | None = None
            
            if gate_model.parameters:
                # Convert string parameters if they represent numbers (e.g. "pi/2")
                params = []
                for p_val in gate_model.parameters:
                    if isinstance(p_val, str):
                        try:
                            # Evaluate simple expressions like "pi/2", "pi"
                            if p_val.lower() == "pi": params.append(np.pi)
                            elif p_val.lower() == "pi/2": params.append(np.pi/2)
                            elif p_val.lower() == "pi/4": params.append(np.pi/4)
                            else: params.append(float(p_val))
                        except ValueError:
                            print(f"Warning: Could not convert string parameter '{p_val}' to float for Cirq. Skipping param.")
                            params.append(0.0) # Default or skip
                    else:
                        params.append(float(p_val))

                if gate_name_lower in ["rx", "ry", "rz"]:
                    gate_instance = cirq_gate_constructor(params[0]) # Assumes rads
                # Add other parameterized gates from CIRQT_GATE_MAP_TO_CIRQT
                # elif gate_name_lower == "u": gate_instance = cirq_gate_constructor(*params) 
                else:
                    # For gates like H, X, CNOT that don't take params but might have them in JSON (should not happen)
                    gate_instance = cirq_gate_constructor 
            else:
                gate_instance = cirq_gate_constructor # This is for classes like cirq.H, cirq.X

            if not isinstance(gate_instance, cirq.Gate): # If constructor was a class
                 gate_instance = gate_instance()


            if gate_instance:
                if gate_model.controls:
                    control_qubits_indices = gate_model.controls
                    cirq_control_qubits = [qubits[i] for i in control_qubits_indices]
                    
                    # Apply controls. Cirq's .controlled_by() is flexible.
                    # For gates like CNOT, CZ, SWAP, they are inherently defined with controls/targets.
                    if gate_name_lower in ["cx", "cnot", "cz", "swap"]:
                         # Ensure correct qubit order for Cirq's CNOT, CZ, SWAP
                        if gate_name_lower in ["cx", "cnot"] and len(cirq_control_qubits) == 1 and len(cirq_target_qubits) == 1:
                            circuit.append(gate_instance(cirq_control_qubits[0], cirq_target_qubits[0]))
                        elif gate_name_lower == "cz" and len(cirq_control_qubits) == 1 and len(cirq_target_qubits) == 1:
                            circuit.append(gate_instance(cirq_control_qubits[0], cirq_target_qubits[0]))
                        elif gate_name_lower == "swap" and len(cirq_target_qubits) == 2: # SWAP takes two targets
                            circuit.append(gate_instance(cirq_target_qubits[0], cirq_target_qubits[1]))
                        else:
                            print(f"Warning: Incorrect qubit count for Cirq gate '{gate_name_lower}'. Appending on targets only.")
                            circuit.append(gate_instance.on(*cirq_target_qubits))
                    else:
                        # General case for other controlled gates
                        controlled_op = gate_instance.on(*cirq_target_qubits).controlled_by(*cirq_control_qubits)
                        circuit.append(controlled_op)
                else:
                    circuit.append(gate_instance.on(*cirq_target_qubits))
            else:
                 print(f"Warning: Could not instantiate Cirq gate for '{gate_model.name}'.")

        except Exception as e:
            print(f"Error applying gate {gate_model.name} to Cirq circuit: {e}")
            import traceback
            traceback.print_exc()
            
    return circuit

def cirq_circuit_to_json(cc: cirq.Circuit, name: str | None = "Converted Cirq Circuit") -> CircuitJSON:
    """
    Converts a Cirq Circuit object to our CircuitJSON model.
    """
    gates_data: list[GateModel] = []
    
    sorted_qubits = sorted(list(cc.all_qubits()), key=lambda q: q.x if isinstance(q, cirq.LineQubit) else str(q))
    qubit_to_index_map = {q: i for i, q in enumerate(sorted_qubits)}
    num_qubits = len(sorted_qubits)

    for moment in cc:
        for op in moment.operations:
            gate = op.gate
            gate_name = _get_cirq_gate_name(gate) # Use helper
            
            op_qubits_indices = [qubit_to_index_map[q] for q in op.qubits if q in qubit_to_index_map]

            targets: list[int] = []
            controls: list[int] | None = None
            parameters: list[float | str] | None = None

            if isinstance(gate, (cirq.ops.Rx, cirq.ops.Ry, cirq.ops.Rz)):
                # These gates store their angle typically as 'exponent * pi' or similar internal representation.
                # For Rx, Ry, Rz, the angle is usually gate.rads, but this might vary.
                # Let's try to get the angle in radians.
                # Cirq's Rx, Ry, Rz gates from cirq.ops take angle_rads in constructor.
                # If the gate object has _rads, use it.
                if hasattr(gate, '_rads'):
                    parameters = [gate._rads]
                elif hasattr(gate, 'angle_rads'): # Check for a direct attribute if _rads isn't there
                    parameters = [gate.angle_rads]
                # Add more specific parameter extraction if needed for other parameterized gates
            elif isinstance(gate, cirq.ops.ZPowGate) and gate.exponent not in [1, 0.5, -0.5, 0.25, -0.25]:
                # For generic ZPowGate (like Phase gate), parameter is the exponent
                # Or could be considered as Rz(exponent * 2 * pi) for some conventions
                # For simplicity, if it's not S, T, Z, Sdg, Tdg, let's store the exponent.
                # This might need adjustment based on how you want to represent generic phase gates.
                 parameters = [gate.exponent] # Or gate.exponent * np.pi for phase
            elif isinstance(gate, cirq.ops.FSimGate):
                parameters = [gate.theta, gate.phi]


            if isinstance(gate, cirq.ops.ControlledGate):
                controls = [qubit_to_index_map[q] for q in gate.control_qubits if q in qubit_to_index_map]
                # The remaining qubits in op.qubits are targets for the sub_gate
                # Need to map sub_gate's qubits based on their role in the original op
                
                # Find target qubits for the sub_gate within the context of the full operation
                sub_gate_target_qubits_in_op = [q for q in op.qubits if q not in gate.control_qubits]
                targets = [qubit_to_index_map[q] for q in sub_gate_target_qubits_in_op if q in qubit_to_index_map]

            elif isinstance(gate, (cirq.ops.CNotPowGate, cirq.ops.CZPowGate)):
                if len(op_qubits_indices) == 2:
                    controls = [op_qubits_indices[0]] # Cirq convention: control first
                    targets = [op_qubits_indices[1]]
                else: 
                    targets = op_qubits_indices
            elif isinstance(gate, cirq.ops.SwapPowGate):
                 if len(op_qubits_indices) == 2:
                    targets = op_qubits_indices
            else: 
                targets = op_qubits_indices
            
            if not targets and op_qubits_indices: 
                targets = op_qubits_indices

            gates_data.append(GateModel(
                name=gate_name.lower(),
                targets=targets,
                controls=controls if controls else None,
                parameters=parameters if parameters else None
            ))
            
    metadata_obj = CircuitMetadata(name=name)
    gate_counts_dict = {}
    for g_model in gates_data:
        gate_counts_dict[g_model.name] = gate_counts_dict.get(g_model.name, 0) + 1
    depth_cirq = None 

    return CircuitJSON(
        num_qubits=num_qubits,
        gates=gates_data,
        metadata=metadata_obj,
        gate_counts=gate_counts_dict if gate_counts_dict else None,
        depth=depth_cirq 
    )

# --- New Pennylane Conversion Code ---

# Mapping from our gate names to Pennylane operation classes or functions
# This needs to be comprehensive for the gates you support.
PENNYLANE_GATE_MAP = {
    "h": qml.Hadamard,
    "x": qml.PauliX,
    "y": qml.PauliY,
    "z": qml.PauliZ,
    "s": qml.S,
    "t": qml.T,
    "rx": qml.RX,
    "ry": qml.RY,
    "rz": qml.RZ,
    "cx": qml.CNOT,
    "cnot": qml.CNOT,
    "cz": qml.CZ,
    "swap": qml.SWAP,
    "id": qml.Identity,
    "toffoli": qml.Toffoli,
    "ccx": qml.Toffoli,
    # Add specific controlled gates if you use these names in CircuitJSON
    "ch": qml.CH,
    "crx": qml.CRX,
    "cry": qml.CRY,
    "crz": qml.CRZ,
    "cswap": qml.CSWAP,
    # "cphase": qml.CPhase, # Example for controlled phase
}

def circuit_json_to_pennylane_script(circuit_json: CircuitJSON, device_name: str = "default.qubit") -> str:
    num_qubits = circuit_json.num_qubits
    script_lines = [
        "import pennylane as qml",
        "from pennylane import numpy as np",
        "",
        f"dev = qml.device('{device_name}', wires={num_qubits})",
        "",
        "@qml.qnode(dev)",
        "def circuit():"
    ]

    if num_qubits == 0:
        script_lines.append("    pass # No qubits in circuit")
        script_lines.append("    return qml.state()")
        return "\n".join(script_lines)

    for gate_model in circuit_json.gates:
        gate_name_lower = gate_model.name.lower()
        pennylane_op_constructor = PENNYLANE_GATE_MAP.get(gate_name_lower)
        
        is_natively_controlled_in_map = gate_name_lower in [
            "cx", "cnot", "cz", "toffoli", "ccx",
            "ch", "crx", "cry", "crz", "cswap"
        ]

        target_wires_str = f"{gate_model.targets}"
        if len(gate_model.targets) == 1:
            target_wires_str = f"{gate_model.targets[0]}"

        params_list_str = []
        if gate_model.parameters:
            for p_val in gate_model.parameters:
                if isinstance(p_val, str):
                    if p_val.lower() == "pi": params_list_str.append("np.pi")
                    elif p_val.lower() == "pi/2": params_list_str.append("np.pi/2")
                    elif p_val.lower() == "pi/4": params_list_str.append("np.pi/4")
                    else:
                        try: float(p_val); params_list_str.append(p_val)
                        except ValueError: params_list_str.append(f"'{p_val}'")
                else:
                    params_list_str.append(str(float(p_val)))
        params_str_for_op = ", ".join(params_list_str)

        op_call = ""

        if gate_model.controls:
            if pennylane_op_constructor and not is_natively_controlled_in_map:
                # Use qml.ctrl() with the found base constructor
                base_op_call_args = []
                if params_str_for_op: base_op_call_args.append(params_str_for_op)
                base_op_call_args.append(f"wires={target_wires_str}")
                base_op_str = f"qml.{pennylane_op_constructor.__name__}({', '.join(base_op_call_args)})"
                
                control_wires_str = f"{gate_model.controls}"
                if len(gate_model.controls) == 1:
                    control_wires_str = f"{gate_model.controls[0]}"
                op_call = f"qml.ctrl({base_op_str}, control={control_wires_str})"

            elif pennylane_op_constructor and is_natively_controlled_in_map:
                # Gate is natively controlled (e.g., CNOT, CH)
                all_wires = gate_model.controls + gate_model.targets
                all_wires_str = f"{all_wires}"
                op_call_args = []
                if params_str_for_op: op_call_args.append(params_str_for_op)
                op_call_args.append(f"wires={all_wires_str}")
                op_call = f"qml.{pennylane_op_constructor.__name__}({', '.join(op_call_args)})"
            
            else: # No pennylane_op_constructor for gate_name_lower, but controls are present
                script_lines.append(f"    # Warning: Gate '{gate_model.name}' (with controls) not found or base for qml.ctrl not identified in PENNYLANE_GATE_MAP. Skipping.")
                continue # Skip this gate

        else: # No controls
            if pennylane_op_constructor:
                op_call_args = []
                if params_str_for_op: op_call_args.append(params_str_for_op)
                if gate_name_lower == "swap" and len(gate_model.targets) == 2:
                     op_call_args.append(f"wires={gate_model.targets}")
                else:
                     op_call_args.append(f"wires={target_wires_str}")
                op_call = f"qml.{pennylane_op_constructor.__name__}({', '.join(op_call_args)})"
            else: # No pennylane_op_constructor and no controls
                script_lines.append(f"    # Warning: Gate '{gate_model.name}' not found in PENNYLANE_GATE_MAP. Skipping.")
                continue # Skip this gate
        
        script_lines.append(f"    {op_call}")

    script_lines.append(f"    return qml.expval(qml.PauliZ(0)) # Example measurement")
    script_lines.append("\n# To run the circuit:")
    script_lines.append("# print(circuit())")
    
    return "\n".join(script_lines)

# ... (rest of the file)