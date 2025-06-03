import { useState, SVGProps } from 'react'; // Added SVGProps
import './App.css';

// Define an interface for the expected CircuitJSON structure from the backend
interface GateModel {
  name: string;
  targets: number[];
  controls?: number[] | null;
  parameters?: (number | string)[] | null;
}

interface CircuitMetadata {
  name?: string | null;
  description?: string | null;
}

interface CircuitJSON {
  num_qubits: number;
  gates: GateModel[];
  metadata?: CircuitMetadata | null;
  gate_counts?: Record<string, number> | null;
  depth?: number | null;
}


// Interface for QASMOutput from backend
interface QASMOutput {
  qasm_string: string;
}


// Simple SVG Circuit Diagram Component
const CircuitDiagram = ({ circuit }: { circuit: CircuitJSON | null }) => {
  if (!circuit || circuit.num_qubits === 0) {
    return <p>No circuit to display or circuit has no qubits.</p>;
  }

  const numQubits = circuit.num_qubits;
  const gates = circuit.gates;

  // Basic dimensions and styling
  const qubitLineSpacing = 50;
  const gateWidth = 40;
  const gateHeight = 40;
  const diagramPadding = 20;
  const timeStepWidth = 60; // Horizontal space for each "moment" or gate column

  // Estimate diagram width based on number of gates (simplistic)
  // A more accurate width would consider parallel gates and circuit depth
  const diagramWidth = diagramPadding * 2 + gates.length * timeStepWidth + gateWidth;
  const diagramHeight = diagramPadding * 2 + (numQubits - 1) * qubitLineSpacing + gateHeight;

  // Gate colors (can be expanded)
  const gateColors: Record<string, string> = {
    h: '#58C4DD', // Light Blue
    x: '#F06292', // Pink
    cx: '#F06292', // Pink for target
    rz: '#4DB6AC', // Teal
    rx: '#FFB74D', // Orange
    // Add more gate colors
    default: '#90A4AE', // Grey
  };

  // Assign a time step (column) to each gate (very basic sequential assignment)
  // This doesn't handle parallel gates correctly yet, just lays them out one after another.
  const gatePositions: Array<{ gate: GateModel; time: number }> = gates.map((gate, index) => ({
    gate,
    time: index,
  }));


  return (
    <div className="circuit-diagram-container">
      <h4>Circuit Diagram (Basic):</h4>
      <svg width={diagramWidth} height={diagramHeight} style={{ border: '1px solid #ccc' }}>
        {/* Draw Qubit Lines */}
        {Array.from({ length: numQubits }).map((_, i) => (
          <line
            key={`qline-${i}`}
            x1={diagramPadding}
            y1={diagramPadding + i * qubitLineSpacing + gateHeight / 2}
            x2={diagramWidth - diagramPadding}
            y2={diagramPadding + i * qubitLineSpacing + gateHeight / 2}
            stroke="#333"
            strokeWidth="1"
          />
        ))}

        {/* Draw Gates */}
        {gatePositions.map(({ gate, time }, gateIndex) => {
          const gateX = diagramPadding + time * timeStepWidth;
          const gateColor = gateColors[gate.name.toLowerCase()] || gateColors.default;

          // Single target gates
          if (gate.targets.length === 1 && (!gate.controls || gate.controls.length === 0)) {
            const targetQubitIndex = gate.targets[0];
            const gateY = diagramPadding + targetQubitIndex * qubitLineSpacing;
            return (
              <g key={`gate-${gateIndex}`}>
                <rect
                  x={gateX}
                  y={gateY}
                  width={gateWidth}
                  height={gateHeight}
                  fill={gateColor}
                  stroke="#333"
                  rx="3"
                  ry="3"
                />
                <text
                  x={gateX + gateWidth / 2}
                  y={gateY + gateHeight / 2 + 5} // +5 for vertical centering adjustment
                  textAnchor="middle"
                  fill="#fff"
                  fontSize="12"
                  fontWeight="bold"
                >
                  {gate.name.toUpperCase()}
                </text>
              </g>
            );
          }
          // CX / CNOT like gates (1 control, 1 target)
          else if (gate.controls && gate.controls.length === 1 && gate.targets.length === 1) {
            const controlQubitIndex = gate.controls[0];
            const targetQubitIndex = gate.targets[0];

            const controlY = diagramPadding + controlQubitIndex * qubitLineSpacing + gateHeight / 2;
            const targetRectY = diagramPadding + targetQubitIndex * qubitLineSpacing;
            const targetCenterY = targetRectY + gateHeight / 2;

            return (
              <g key={`gate-${gateIndex}`}>
                {/* Control Line */}
                <line
                  x1={gateX + gateWidth / 2}
                  y1={controlY}
                  x2={gateX + gateWidth / 2}
                  y2={targetCenterY}
                  stroke="#333"
                  strokeWidth="2"
                />
                {/* Control Dot */}
                <circle
                  cx={gateX + gateWidth / 2}
                  cy={controlY}
                  r="5"
                  fill="#333"
                />
                {/* Target Gate (e.g., X part of CX) */}
                <rect
                  x={gateX}
                  y={targetRectY}
                  width={gateWidth}
                  height={gateHeight}
                  fill={gateColor}
                  stroke="#333"
                  rx="3"
                  ry="3"
                />
                <text // Typically, the target operation (e.g., X for CX)
                  x={gateX + gateWidth / 2}
                  y={targetRectY + gateHeight / 2 + 5}
                  textAnchor="middle"
                  fill="#fff"
                  fontSize="12"
                  fontWeight="bold"
                >
                  {gate.name.toUpperCase().includes('X') ? 'X' : gate.name.toUpperCase()}
                </text>
              </g>
            );
          }
          // Placeholder for other multi-qubit gates or unhandled types
          return (
             <g key={`gate-${gateIndex}-placeholder`}>
                <rect
                  x={gateX}
                  y={diagramPadding + gate.targets[0] * qubitLineSpacing} // Default to first target
                  width={gateWidth}
                  height={gateHeight}
                  fill={gateColors.default}
                  stroke="#666"
                  rx="3"
                  ry="3"
                />
                <text
                  x={gateX + gateWidth / 2}
                  y={diagramPadding + gate.targets[0] * qubitLineSpacing + gateHeight / 2 + 5}
                  textAnchor="middle"
                  fill="#fff"
                  fontSize="10"
                >
                  {gate.name.toUpperCase()}
                </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};


function App() {
  const [qasmInput, setQasmInput] = useState<string>("OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\nh q[0];\ncx q[0], q[1];\nrx(pi/2) q[0];"); // Example with 2 qubits
  const [parsedCircuit, setParsedCircuit] = useState<CircuitJSON | null>(null);
  const [optimizedCircuit, setOptimizedCircuit] = useState<CircuitJSON | null>(null);
  const [exportedQasm, setExportedQasm] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isOptimizing, setIsOptimizing] = useState<boolean>(false);
  const [isExporting, setIsExporting] = useState<boolean>(false);

  const API_BASE_URL = 'http://localhost:8000';

  const handleParseQasm = async () => {
    setIsLoading(true);
    setError(null);
    setParsedCircuit(null);
    setOptimizedCircuit(null); // Clear previous optimization results
    setExportedQasm(null);    // Clear previous export results
    try {
      const response = await fetch(`${API_BASE_URL}/circuit/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ qasm_string: qasmInput }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      const data: CircuitJSON = await response.json();
      setParsedCircuit(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred.');
      console.error("Failed to parse QASM:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOptimizeCircuit = async () => {
    if (!parsedCircuit) {
      setError("Please parse a circuit first.");
      return;
    }
    setIsOptimizing(true);
    setError(null);
    setOptimizedCircuit(null);
    setExportedQasm(null);

    try {
      const response = await fetch(`${API_BASE_URL}/circuit/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          circuit: parsedCircuit,
          passes: ["remove_self_inverse_pairs"] // Using our defined pass
        }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      const data: CircuitJSON = await response.json();
      setOptimizedCircuit(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred.');
      console.error("Failed to optimize circuit:", err);
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleExportQasm = async (circuitToExport: CircuitJSON | null) => {
    if (!circuitToExport) {
      setError("No circuit available to export.");
      return;
    }
    setIsExporting(true);
    setError(null);
    setExportedQasm(null);
    try {
      const response = await fetch(`${API_BASE_URL}/circuit/export/qasm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(circuitToExport),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      const data: QASMOutput = await response.json();
      setExportedQasm(data.qasm_string);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred.');
      console.error("Failed to export QASM:", err);
    } finally {
      setIsExporting(false);
    }
  };


  // Helper component to display circuit details (textual)
  const CircuitDetailsView = ({ circuit, title }: { circuit: CircuitJSON, title: string }) => (
    <div className="circuit-details-view">
      <h3>{title}</h3>
      <p><strong>Number of Qubits:</strong> {circuit.num_qubits}</p>
      {circuit.gate_counts && (
        <p><strong>Gate Counts:</strong> {JSON.stringify(circuit.gate_counts)}</p>
      )}
      {circuit.depth !== null && circuit.depth !== undefined && (
         <p><strong>Depth:</strong> {circuit.depth}</p>
      )}
      <h4>Gates:</h4>
      <pre>{JSON.stringify(circuit.gates, null, 2)}</pre>
      {circuit.metadata?.name && (
        <p><strong>Metadata Name:</strong> {circuit.metadata.name}</p>
      )}
    </div>
  );

  return (
    <div className="App">
      <h1>QuantumCanvas Circuit Tools</h1>
      <div className="input-section">
        <textarea
          value={qasmInput}
          onChange={(e) => setQasmInput(e.target.value)}
          rows={10}
          cols={80}
          placeholder="Enter OpenQASM 2.0 string here..."
        />
        <button onClick={handleParseQasm} disabled={isLoading}>
          {isLoading ? 'Parsing...' : 'Parse QASM'}
        </button>
      </div>

      {error && (
        <div className="error-message">
          <p>Error: {error}</p>
        </div>
      )}

      <div className="results-container">
        {parsedCircuit && (
          <div className="output-section parsed-section">
            <CircuitDetailsView circuit={parsedCircuit} title="Parsed Circuit Details" />
            <CircuitDiagram circuit={parsedCircuit} /> {/* Add Diagram for Parsed */}
            <div className="actions-bar">
              <button onClick={handleOptimizeCircuit} disabled={isOptimizing || isLoading}>
                {isOptimizing ? 'Optimizing...' : 'Optimize (Remove H-H)'}
              </button>
              <button onClick={() => handleExportQasm(parsedCircuit)} disabled={isExporting || isLoading}>
                {isExporting ? 'Exporting...' : 'Export Parsed to QASM'}
              </button>
            </div>
          </div>
        )}

        {optimizedCircuit && (
          <div className="output-section optimized-section">
            <CircuitDetailsView circuit={optimizedCircuit} title="Optimized Circuit Details" />
            <CircuitDiagram circuit={optimizedCircuit} /> {/* Add Diagram for Optimized */}
             <div className="actions-bar">
              <button onClick={() => handleExportQasm(optimizedCircuit)} disabled={isExporting || isLoading || isOptimizing}>
                {isExporting ? 'Exporting...' : 'Export Optimized to QASM'}
              </button>
            </div>
          </div>
        )}
      </div>

      {exportedQasm && (
        <div className="output-section export-section">
          <h3>Exported QASM:</h3>
          <textarea
            value={exportedQasm}
            readOnly
            rows={10}
            cols={80}
          />
        </div>
      )}
    </div>
  );
}

export default App;
