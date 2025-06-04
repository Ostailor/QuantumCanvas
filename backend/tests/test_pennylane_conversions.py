import pytest
from app.models import CircuitJSON, GateModel, CircuitMetadata
from app.utils.circuit_conversions import circuit_json_to_pennylane_script

def test_empty_circuit_to_pennylane_script():
    circuit_json = CircuitJSON(
        num_qubits=0,
        gates=[],
        metadata=CircuitMetadata(name="Empty Pennylane Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    assert "import pennylane as qml" in script
    assert "dev = qml.device('default.qubit', wires=0)" in script
    assert "@qml.qnode(dev)" in script
    assert "def circuit():" in script
    assert "    pass # No qubits in circuit" in script
    assert "    return qml.state()" in script # CORRECTED ASSERTION

def test_single_hadamard_to_pennylane_script():
    circuit_json = CircuitJSON(
        num_qubits=1,
        gates=[GateModel(name="h", targets=[0])],
        metadata=CircuitMetadata(name="Hadamard Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    assert "dev = qml.device('default.qubit', wires=1)" in script
    assert "    qml.Hadamard(wires=0)" in script
    assert "    return qml.expval(qml.PauliZ(0))" in script

def test_cnot_to_pennylane_script():
    circuit_json = CircuitJSON(
        num_qubits=2,
        gates=[GateModel(name="cx", controls=[0], targets=[1])],
        metadata=CircuitMetadata(name="CNOT Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    assert "dev = qml.device('default.qubit', wires=2)" in script
    assert "    qml.CNOT(wires=[0, 1])" in script

def test_rx_gate_with_param_to_pennylane_script():
    circuit_json = CircuitJSON(
        num_qubits=1,
        gates=[GateModel(name="rx", targets=[0], parameters=[1.57079632679])], # pi/2
        metadata=CircuitMetadata(name="RX Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    assert "    qml.RX(1.57079632679, wires=0)" in script

def test_rx_gate_with_pi_param_to_pennylane_script():
    circuit_json = CircuitJSON(
        num_qubits=1,
        gates=[GateModel(name="rx", targets=[0], parameters=["pi/2"])],
        metadata=CircuitMetadata(name="RX Pi Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    # Expecting the string "np.pi/2" for the parameter
    assert "    qml.RX(np.pi/2, wires=0)" in script
    assert "from pennylane import numpy as np" in script


def test_toffoli_gate_to_pennylane_script():
    circuit_json = CircuitJSON(
        num_qubits=3,
        gates=[GateModel(name="toffoli", controls=[0, 1], targets=[2])],
        metadata=CircuitMetadata(name="Toffoli Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    assert "dev = qml.device('default.qubit', wires=3)" in script
    assert "    qml.Toffoli(wires=[0, 1, 2])" in script

def test_unknown_gate_to_pennylane_script():
    circuit_json = CircuitJSON(
        num_qubits=1,
        gates=[GateModel(name="unknown_gate", targets=[0])],
        metadata=CircuitMetadata(name="Unknown Gate Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    assert "    # Warning: Gate 'unknown_gate' not found in PENNYLANE_GATE_MAP. Skipping." in script

def test_circuit_with_multiple_gates():
    circuit_json = CircuitJSON(
        num_qubits=2,
        gates=[
            GateModel(name="h", targets=[0]),
            GateModel(name="cx", controls=[0], targets=[1]),
            GateModel(name="rz", targets=[1], parameters=[0.5])
        ],
        metadata=CircuitMetadata(name="Multi-Gate Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    assert "    qml.Hadamard(wires=0)" in script
    assert "    qml.CNOT(wires=[0, 1])" in script
    assert "    qml.RZ(0.5, wires=1)" in script

# --- New tests for refined control handling ---

def test_generic_controlled_h_to_pennylane_script():
    circuit_json = CircuitJSON(
        num_qubits=2,
        gates=[GateModel(name="h", targets=[1], controls=[0])],
        metadata=CircuitMetadata(name="Controlled-H Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    assert "dev = qml.device('default.qubit', wires=2)" in script
    # Expected: qml.ctrl(qml.Hadamard(wires=1), control=0)
    assert "    qml.ctrl(qml.Hadamard(wires=1), control=0)" in script
    assert "    return qml.expval(qml.PauliZ(0))" in script

def test_explicitly_mapped_ch_to_pennylane_script():
    circuit_json = CircuitJSON(
        num_qubits=2,
        gates=[GateModel(name="ch", targets=[1], controls=[0])], # Assuming CH takes control as first wire
        metadata=CircuitMetadata(name="Explicit CH Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    assert "dev = qml.device('default.qubit', wires=2)" in script
    # Expected: qml.CH(wires=[0, 1])
    assert "    qml.CH(wires=[0, 1])" in script

def test_generic_multi_controlled_x_to_pennylane_script():
    # Simulating a Toffoli using a base 'x' gate with two controls
    circuit_json = CircuitJSON(
        num_qubits=3,
        gates=[GateModel(name="x", targets=[2], controls=[0, 1])],
        metadata=CircuitMetadata(name="Generic CCX Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    assert "dev = qml.device('default.qubit', wires=3)" in script
    # Expected: qml.ctrl(qml.PauliX(wires=2), control=[0, 1])
    assert "    qml.ctrl(qml.PauliX(wires=2), control=[0, 1])" in script

def test_generic_controlled_rx_to_pennylane_script():
    circuit_json = CircuitJSON(
        num_qubits=2,
        gates=[GateModel(name="rx", targets=[1], controls=[0], parameters=[0.785])], # pi/4
        metadata=CircuitMetadata(name="Controlled-RX Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    assert "dev = qml.device('default.qubit', wires=2)" in script
    # Expected: qml.ctrl(qml.RX(0.785, wires=1), control=0)
    assert "    qml.ctrl(qml.RX(0.785, wires=1), control=0)" in script

def test_explicitly_mapped_crx_to_pennylane_script():
    circuit_json = CircuitJSON(
        num_qubits=2,
        gates=[GateModel(name="crx", targets=[1], controls=[0], parameters=[0.785])],
        metadata=CircuitMetadata(name="Explicit CRX Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    assert "dev = qml.device('default.qubit', wires=2)" in script
    # Expected: qml.CRX(0.785, wires=[0, 1])
    assert "    qml.CRX(0.785, wires=[0, 1])" in script

def test_toffoli_still_works(): # Ensure existing specific gates are not broken
    circuit_json = CircuitJSON(
        num_qubits=3,
        gates=[GateModel(name="toffoli", controls=[0, 1], targets=[2])],
        metadata=CircuitMetadata(name="Toffoli Test Existing")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    assert "    qml.Toffoli(wires=[0, 1, 2])" in script

def test_unhandled_controlled_gate_warning():
    circuit_json = CircuitJSON(
        num_qubits=2,
        gates=[GateModel(name="unknown_base_gate", targets=[1], controls=[0])],
        metadata=CircuitMetadata(name="Unknown Controlled Gate Test")
    )
    script = circuit_json_to_pennylane_script(circuit_json)
    expected_warning = "    # Warning: Gate 'unknown_base_gate' (with controls) not found or base for qml.ctrl not identified in PENNYLANE_GATE_MAP. Skipping."
    assert expected_warning in script

# --- End of new tests ---