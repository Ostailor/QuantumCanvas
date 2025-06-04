import { useState, SVGProps } from 'react';
import './App.css'; // Assuming App.css contains the previous styles
// Import shadcn/ui components that were used before the major overhaul
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

// Interfaces
interface GateModel {
  name: string;
  targets: number[];
  controls: number[] | null;
  parameters: (number | string)[] | null; // Allow string for "pi/2" etc.
}

interface CircuitMetadata {
  name?: string;
  // Add other metadata fields if any
}

interface CircuitJSON {
  num_qubits: number;
  gates: GateModel[];
  metadata?: CircuitMetadata;
  gate_counts?: Record<string, number>;
  depth?: number;
}

interface QASMOutput {
  qasm_string: string;
}

interface PennylaneScriptOutput {
  script: string;
  message?: string | null;
}


// Helper for diagram (simplified, assuming it was like this or similar)
interface PositionedGate {
  gate: GateModel;
  column: number;
}

const calculateGateColumns = (gates: GateModel[], numQubits: number): { positionedGates: PositionedGate[], totalColumns: number } => {
  const qubitAvailability: number[] = Array(numQubits).fill(0); // Next available column for each qubit
  const positionedGates: PositionedGate[] = [];
  let totalColumns = 0;

  gates.forEach(gate => {
    let currentGateColumn = 0;
    const involvedQubits = [...(gate.controls || []), ...gate.targets];
    involvedQubits.forEach(q => {
      if (q < numQubits) { // Ensure qubit index is valid
        currentGateColumn = Math.max(currentGateColumn, qubitAvailability[q]);
      }
    });

    positionedGates.push({ gate, column: currentGateColumn });

    involvedQubits.forEach(q => {
      if (q < numQubits) {
        qubitAvailability[q] = currentGateColumn + 1;
      }
    });
    totalColumns = Math.max(totalColumns, currentGateColumn + 1);
  });

  return { positionedGates, totalColumns };
};

const CircuitDiagram = ({ circuit }: { circuit: CircuitJSON | null }) => {
  if (!circuit || circuit.num_qubits === 0) {
    return <p className="text-sm text-muted-foreground mt-2">No circuit to display.</p>;
  }

  const numQubits = circuit.num_qubits;
  const { positionedGates, totalColumns } = calculateGateColumns(circuit.gates, numQubits);

  const qubitLineSpacing = 50;
  const gateWidth = 40;
  const gateHeight = 40;
  const diagramPadding = 20;
  const timeStepWidth = 60;

  const diagramWidth = diagramPadding * 2 + totalColumns * timeStepWidth;
  const diagramHeight = diagramPadding * 2 + (numQubits - 1) * qubitLineSpacing + gateHeight;

  // Basic gate colors, can be expanded
  const gateColors: Record<string, string> = {
    h: '#64B5F6', // Light Blue
    x: '#E57373', // Light Red
    cx: '#E57373',
    rz: '#81C784', // Light Green
    rx: '#FFB74D', // Orange
    default: '#B0BEC5', // Blue Grey
  };

  return (
    <div className="circuit-diagram-container mt-4 overflow-x-auto">
      <h4 className="text-md font-semibold mb-2">Circuit Diagram:</h4>
      <svg width={diagramWidth} height={diagramHeight} className="border rounded bg-slate-50">
        {Array.from({ length: numQubits }).map((_, i) => (
          <line
            key={`qline-${i}`}
            x1={diagramPadding}
            y1={diagramPadding + i * qubitLineSpacing + gateHeight / 2}
            x2={diagramWidth - diagramPadding}
            y2={diagramPadding + i * qubitLineSpacing + gateHeight / 2}
            stroke="#90A4AE"
            strokeWidth="1"
          />
        ))}
        {positionedGates.map(({ gate, column }, gateIndex) => {
          const gateX = diagramPadding + column * timeStepWidth;
          const gateColor = gateColors[gate.name.toLowerCase()] || gateColors.default;

          if (gate.targets.length === 1 && (!gate.controls || gate.controls.length === 0)) {
            const targetQubitIndex = gate.targets[0];
            if (targetQubitIndex >= numQubits) return null;
            const gateY = diagramPadding + targetQubitIndex * qubitLineSpacing;
            return (
              <g key={`gate-${gateIndex}`}>
                <rect x={gateX} y={gateY} width={gateWidth} height={gateHeight} fill={gateColor} stroke="#546E7A" rx="3" />
                <text x={gateX + gateWidth / 2} y={gateY + gateHeight / 2 + 4} textAnchor="middle" fill="white" fontSize="12">
                  {gate.name.toUpperCase()}
                </text>
              </g>
            );
          } else if (gate.controls && gate.controls.length === 1 && gate.targets.length === 1) {
            const controlQubitIndex = gate.controls[0];
            const targetQubitIndex = gate.targets[0];
            if (controlQubitIndex >= numQubits || targetQubitIndex >= numQubits) return null;

            const controlY = diagramPadding + controlQubitIndex * qubitLineSpacing + gateHeight / 2;
            const targetRectY = diagramPadding + targetQubitIndex * qubitLineSpacing;
            const targetCenterY = targetRectY + gateHeight / 2;
            return (
              <g key={`gate-${gateIndex}`}>
                <line x1={gateX + gateWidth / 2} y1={controlY} x2={gateX + gateWidth / 2} y2={targetCenterY} stroke="#546E7A" strokeWidth="2" />
                <circle cx={gateX + gateWidth / 2} cy={controlY} r="5" fill="#546E7A" />
                <rect x={gateX} y={targetRectY} width={gateWidth} height={gateHeight} fill={gateColor} stroke="#546E7A" rx="3" />
                <text x={gateX + gateWidth / 2} y={targetRectY + gateHeight / 2 + 4} textAnchor="middle" fill="white" fontSize="12">
                  {gate.name.toUpperCase().includes('X') ? 'X' : gate.name.toUpperCase()}
                </text>
              </g>
            );
          }
          // Placeholder for other complex gates
          const firstTargetIdx = gate.targets[0];
          if (firstTargetIdx >= numQubits) return null;
          return (
            <g key={`gate-${gateIndex}-placeholder`}>
              <rect x={gateX} y={diagramPadding + firstTargetIdx * qubitLineSpacing} width={gateWidth} height={gateHeight} fill={gateColors.default} stroke="#546E7A" rx="3"/>
              <text x={gateX + gateWidth / 2} y={diagramPadding + firstTargetIdx * qubitLineSpacing + gateHeight / 2 + 4} textAnchor="middle" fill="white" fontSize="10">
                {gate.name.toUpperCase()}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};


const CircuitDetailsView = ({ circuit, title }: { circuit: CircuitJSON, title: string }) => (
  <div className="circuit-details mb-3">
    <h3 className="text-lg font-semibold">{title}</h3>
    <p className="text-sm">Qubits: {circuit.num_qubits}</p>
    {circuit.gate_counts && <p className="text-sm">Gate Counts: {JSON.stringify(circuit.gate_counts)}</p>}
    {circuit.depth !== null && circuit.depth !== undefined && <p className="text-sm">Depth: {circuit.depth}</p>}
    {circuit.metadata?.name && <p className="text-sm">Name: {circuit.metadata.name}</p>}
    <Label htmlFor={`gates-json-${title.replace(/\s+/g, '-')}`} className="text-sm font-medium mt-1 block">Gates (JSON):</Label>
    <pre id={`gates-json-${title.replace(/\s+/g, '-')}`} className="text-xs bg-gray-100 p-2 border rounded overflow-x-auto max-h-48">
      {JSON.stringify(circuit.gates, null, 2)}
    </pre>
  </div>
);

function App() {
  const [qasmInput, setQasmInput] = useState<string>("OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\nh q[0];\nh q[1];\ncx q[0], q[1];\nrx(pi/2) q[0];");
  const [parsedCircuit, setParsedCircuit] = useState<CircuitJSON | null>(null);
  const [optimizedCircuit, setOptimizedCircuit] = useState<CircuitJSON | null>(null);
  const [exportedQasm, setExportedQasm] = useState<string | null>(null);
  const [exportedPennylaneScript, setExportedPennylaneScript] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isOptimizing, setIsOptimizing] = useState<boolean>(false);
  const [isExportingQasm, setIsExportingQasm] = useState<boolean>(false);
  const [isExportingPennylane, setIsExportingPennylane] = useState<boolean>(false);

  const API_BASE_URL = 'http://localhost:8000';

  const handleParseQasm = async () => {
    setIsLoading(true);
    setError(null);
    setParsedCircuit(null);
    setOptimizedCircuit(null);
    setExportedQasm(null);
    setExportedPennylaneScript(null);
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
      setError(err instanceof Error ? err.message : 'An unknown error occurred during parsing.');
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
    setExportedPennylaneScript(null);
    try {
      const response = await fetch(`${API_BASE_URL}/circuit/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          circuit: parsedCircuit,
          passes: ["remove_self_inverse_pairs"] 
        }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      const data: CircuitJSON = await response.json();
      setOptimizedCircuit(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred during optimization.');
      console.error("Failed to optimize circuit:", err);
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleExportQasm = async (circuitToExport: CircuitJSON | null) => {
    if (!circuitToExport) {
      setError("No circuit available to export QASM.");
      return;
    }
    setIsExportingQasm(true);
    setError(null);
    setExportedQasm(null);
    setExportedPennylaneScript(null); 
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
      setError(err instanceof Error ? err.message : 'An unknown error occurred while exporting QASM.');
      console.error("Failed to export QASM:", err);
    } finally {
      setIsExportingQasm(false);
    }
  };

  const handleExportPennylaneScript = async (circuitToExport: CircuitJSON | null) => {
    if (!circuitToExport) {
      setError("No circuit available to export to Pennylane script.");
      return;
    }
    setIsExportingPennylane(true);
    setError(null);
    setExportedPennylaneScript(null);
    setExportedQasm(null); 
    try {
      const response = await fetch(`${API_BASE_URL}/circuit/export/pennylane_script`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(circuitToExport),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      const data: PennylaneScriptOutput = await response.json();
      setExportedPennylaneScript(data.script);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred while exporting Pennylane script.');
      console.error("Failed to export Pennylane script:", err);
    } finally {
      setIsExportingPennylane(false);
    }
  };

  return (
    <div className="App p-4"> {/* Basic padding, App.css might provide more */}
      <header className="mb-4">
        <h1 className="text-2xl font-bold text-center">QuantumCanvas Circuit Tools</h1>
      </header>

      <div className="input-section mb-4 p-3 border rounded bg-white shadow">
        <Label htmlFor="qasm-input" className="text-md font-medium mb-1 block">OpenQASM 2.0 Input:</Label>
        <Textarea
          id="qasm-input"
          value={qasmInput}
          onChange={(e) => setQasmInput(e.target.value)}
          rows={8}
          placeholder="Enter OpenQASM 2.0 string here..."
          className="mb-2 w-full"
        />
        <Button onClick={handleParseQasm} disabled={isLoading} className="w-full sm:w-auto">
          {isLoading ? 'Parsing...' : 'Parse QASM'}
        </Button>
      </div>

      {error && (
        <div className="error-message p-2 mb-3 bg-red-100 text-red-700 border border-red-300 rounded">
          <p>Error: {error}</p>
        </div>
      )}

      <div className="results-container grid md:grid-cols-2 gap-4 mb-4">
        {parsedCircuit && (
          <div className="output-section parsed-section p-3 border rounded bg-white shadow">
            <CircuitDetailsView circuit={parsedCircuit} title="Parsed Circuit" />
            <CircuitDiagram circuit={parsedCircuit} />
            <div className="actions-bar mt-3 space-x-2">
              <Button onClick={handleOptimizeCircuit} disabled={isOptimizing || isLoading} variant="outline" size="sm">
                {isOptimizing ? 'Optimizing...' : 'Optimize (H-H)'}
              </Button>
              <Button onClick={() => handleExportQasm(parsedCircuit)} disabled={isExportingQasm || isLoading} variant="outline" size="sm">
                {isExportingQasm ? 'Exporting...' : 'Export Parsed QASM'}
              </Button>
              <Button onClick={() => handleExportPennylaneScript(parsedCircuit)} disabled={isExportingPennylane || isLoading} variant="outline" size="sm">
                {isExportingPennylane ? 'Exporting...' : 'Export Parsed PL'}
              </Button>
            </div>
          </div>
        )}

        {optimizedCircuit && (
          <div className="output-section optimized-section p-3 border rounded bg-white shadow">
            <CircuitDetailsView circuit={optimizedCircuit} title="Optimized Circuit" />
            <CircuitDiagram circuit={optimizedCircuit} />
            <div className="actions-bar mt-3 space-x-2">
              <Button onClick={() => handleExportQasm(optimizedCircuit)} disabled={isExportingQasm || isLoading || isOptimizing} variant="outline" size="sm">
                {isExportingQasm ? 'Exporting...' : 'Export Optimized QASM'}
              </Button>
              <Button onClick={() => handleExportPennylaneScript(optimizedCircuit)} disabled={isExportingPennylane || isLoading || isOptimizing} variant="outline" size="sm">
                {isExportingPennylane ? 'Exporting...' : 'Export Optimized PL'}
              </Button>
            </div>
          </div>
        )}
      </div>

      {exportedQasm && (
        <div className="output-section export-section mt-4 p-3 border rounded bg-white shadow">
          <Label htmlFor="qasm-output" className="text-md font-medium mb-1 block">Exported QASM:</Label>
          <Textarea
            id="qasm-output"
            value={exportedQasm}
            readOnly
            rows={10}
            className="font-mono text-sm w-full"
          />
        </div>
      )}

      {exportedPennylaneScript && (
        <div className="output-section export-section mt-4 p-3 border rounded bg-white shadow">
          <Label htmlFor="pennylane-output" className="text-md font-medium mb-1 block">Exported Pennylane Script:</Label>
          <Textarea
            id="pennylane-output"
            value={exportedPennylaneScript}
            readOnly
            rows={12}
            className="font-mono text-sm w-full"
          />
        </div>
      )}
    </div>
  );
}

export default App;
