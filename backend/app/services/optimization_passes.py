from app.models import CircuitJSON, GateModel
from typing import List

def remove_self_inverse_pairs(circuit_json: CircuitJSON) -> CircuitJSON:
    """
    Removes adjacent identical single-qubit gates that are their own inverse (e.g., H-H, X-X).
    This is a very basic optimization pass.
    """
    optimized_gates: List[GateModel] = []
    
    # Gates that are their own inverse and are single-qubit
    # (and don't typically have parameters that would change their inverse property)
    SELF_INVERSE_SINGLE_QUBIT_GATES = {"h", "x", "y", "z"} 

    i = 0
    gates = circuit_json.gates
    num_original_gates = len(gates)

    while i < num_original_gates:
        current_gate = gates[i]
        
        if i + 1 < num_original_gates:
            next_gate = gates[i+1]
            
            # Check for a pair to remove
            is_self_inverse_type = current_gate.name.lower() in SELF_INVERSE_SINGLE_QUBIT_GATES
            is_single_qubit_current = len(current_gate.targets) == 1 and not current_gate.controls
            is_single_qubit_next = len(next_gate.targets) == 1 and not next_gate.controls

            if (is_self_inverse_type and
                is_single_qubit_current and is_single_qubit_next and
                current_gate.name == next_gate.name and
                current_gate.targets == next_gate.targets and # Same qubit
                not current_gate.parameters and not next_gate.parameters): # No parameters
                
                # Skip both gates
                i += 2
                continue
        
        # If no pair was removed, add the current gate and move to the next
        optimized_gates.append(current_gate)
        i += 1
        
    # Create a new CircuitJSON. Recalculating stats would be ideal here.
    # For simplicity, we'll copy metadata and num_qubits, but stats will be outdated.
    # A more robust implementation would convert to Qiskit, get new stats, then convert back.
    return CircuitJSON(
        num_qubits=circuit_json.num_qubits,
        gates=optimized_gates,
        metadata=circuit_json.metadata,
        # gate_counts and depth would ideally be recalculated here.
        # For now, they will be None or copied from original, which is inaccurate.
        gate_counts=None, # Mark as needing recalculation
        depth=None        # Mark as needing recalculation
    )

# You can add more optimization passes here
OPTIMIZATION_PASS_REGISTRY = {
    "remove_self_inverse_pairs": remove_self_inverse_pairs,
    # "another_optimization_pass": another_optimization_function,
}