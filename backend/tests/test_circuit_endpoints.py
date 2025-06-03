from fastapi.testclient import TestClient
from app.main import app # Assuming your FastAPI app instance is named 'app' in 'app.main'
from app.models import CircuitJSON # To validate response structure

client = TestClient(app)

def test_parse_simple_qasm():
    qasm_string = "OPENQASM 2.0; include \"qelib1.inc\"; qreg q[1]; h q[0];"
    response = client.post("/circuit/parse", json={"qasm_string": qasm_string})
    assert response.status_code == 200
    data = response.json()
    
    assert data["num_qubits"] == 1
    assert len(data["gates"]) == 1
    assert data["gates"][0]["name"] == "h"
    assert data["gates"][0]["targets"] == [0]
    assert data["gate_counts"] == {"h": 1}
    assert data["depth"] is not None # Check that depth is calculated

def test_parse_qasm_with_cx():
    qasm_string = "OPENQASM 2.0; include \"qelib1.inc\"; qreg q[2]; cx q[0], q[1];"
    response = client.post("/circuit/parse", json={"qasm_string": qasm_string})
    assert response.status_code == 200
    data = response.json()

    assert data["num_qubits"] == 2
    assert len(data["gates"]) == 1
    assert data["gates"][0]["name"] == "cx"
    assert data["gates"][0]["controls"] == [0]
    assert data["gates"][0]["targets"] == [1]
    assert data["gate_counts"] == {"cx": 1}

def test_parse_invalid_qasm_version():
    qasm_string = "OPENQASM 3.0; qubit q; h q;" # Not QASM 2.0
    response = client.post("/circuit/parse", json={"qasm_string": qasm_string})
    assert response.status_code == 400 # Expecting bad request
    assert "Only OpenQASM 2.0 strings are supported" in response.json()["detail"]

def test_optimize_remove_hh_pair():
    # This circuit JSON represents a circuit with h q[0]; h q[0]; x q[0];
    circuit_to_optimize = {
        "num_qubits": 1,
        "gates": [
            {"name": "h", "targets": [0], "controls": None, "parameters": None},
            {"name": "h", "targets": [0], "controls": None, "parameters": None},
            {"name": "x", "targets": [0], "controls": None, "parameters": None}
        ],
        "metadata": {"name": "Test HHX Circuit"},
        "gate_counts": {"h": 2, "x": 1}, # Initial counts
        "depth": 3 # Initial depth
    }
    
    optimization_request = {
        "circuit": circuit_to_optimize,
        "passes": ["remove_self_inverse_pairs"]
    }
    
    response = client.post("/circuit/optimize", json=optimization_request)
    assert response.status_code == 200
    data = response.json()
    
    # After H-H removal, only X gate should remain
    assert data["num_qubits"] == 1
    assert len(data["gates"]) == 1
    assert data["gates"][0]["name"] == "x"
    assert data["gate_counts"] == {"x": 1} # Stats should be recalculated
    assert data["depth"] == 1 # Depth should be recalculated

def test_optimize_unknown_pass():
    circuit_to_optimize = {
        "num_qubits": 1,
        "gates": [{"name": "h", "targets": [0]}],
        "metadata": {"name": "Test H Circuit"},
        "gate_counts": {"h": 1},
        "depth": 1
    }
    optimization_request = {
        "circuit": circuit_to_optimize,
        "passes": ["non_existent_pass"]
    }
    response = client.post("/circuit/optimize", json=optimization_request)
    assert response.status_code == 200 # Currently, unknown passes are ignored and original circuit returned
    data = response.json()
    assert len(data["gates"]) == 1 # Should be unchanged
    assert data["gates"][0]["name"] == "h"

def test_export_qasm_simple():
    circuit_json = {
        "num_qubits": 1,
        "gates": [{"name": "h", "targets": [0]}],
        "metadata": {"name": "Test H Circuit"}
    }
    response = client.post("/circuit/export/qasm", json=circuit_json)
    assert response.status_code == 200
    data = response.json()
    assert "OPENQASM 2.0;" in data["qasm_string"]
    assert "qreg q[1];" in data["qasm_string"]
    assert "h q[0];" in data["qasm_string"]

# You can add more tests, including for edge cases or using Hypothesis for property-based testing.