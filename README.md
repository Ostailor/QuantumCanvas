# QuantumCanvas

QuantumCanvas is a web application designed for parsing, visualizing, optimizing, and converting quantum circuits. It features a Python-based backend with FastAPI and a React/TypeScript frontend.

## Project Structure

```
QuantumCanvas/
├── backend/            # FastAPI application
│   ├── app/
│   │   ├── main.py         # FastAPI app initialization and CORS
│   │   ├── models.py       # Pydantic models for data structures (CircuitJSON, GateModel, etc.)
│   │   ├── routers/
│   │   │   └── circuit.py  # API endpoints for circuit operations
│   │   ├── services/
│   │   │   └── optimization_passes.py # Circuit optimization algorithms
│   │   └── utils/
│   │       └── circuit_conversions.py # Logic for converting between circuit formats
│   ├── tests/              # Pytest unit tests for backend logic
│   ├── pyproject.toml    # Project dependencies and metadata (Poetry)
│   └── README.md         # Backend specific details (currently empty)
├── frontend/           # React/Vite application
│   ├── public/
│   ├── src/
│   │   ├── App.tsx         # Main application component, state management, API calls
│   │   ├── main.tsx        # Entry point for the React application
│   │   ├── components/ui/  # Reusable UI components (Button, Textarea, Card, etc.)
│   │   ├── lib/utils.ts    # Utility functions (e.g., `cn` for classnames)
│   │   └── index.css       # Global styles and TailwindCSS base
│   ├── index.html        # Main HTML file
│   ├── vite.config.ts    # Vite configuration
│   ├── tailwind.config.js # TailwindCSS configuration
│   ├── tsconfig.json     # TypeScript configuration
│   └── package.json      # Frontend dependencies and scripts (npm/yarn/pnpm)
└── .gitignore          # Git ignore rules for the entire project
```

## Backend Implementation (Python/FastAPI)

The backend is built using FastAPI and handles the core quantum circuit logic.

### Core Functionality

1.  **QASM Parsing:**
    *   Incoming OpenQASM 2.0 strings are parsed using Qiskit's `qiskit.qasm2.loads` function.
    *   The endpoint [`/circuit/parse`](/Users/omtailor/QuantumCanvas/backend/app/routers/circuit.py) handles this. It currently enforces that the input string starts with `OPENQASM 2.0;`.
    *   The parsed Qiskit `QuantumCircuit` is then converted into a custom `CircuitJSON` model.

2.  **Internal Circuit Representation (`CircuitJSON`):**
    *   Defined in [`app/models.py`](/Users/omtailor/QuantumCanvas/backend/app/models.py), `CircuitJSON` is the primary data structure for representing quantum circuits within the backend.
    *   It includes:
        *   `num_qubits`: Total number of qubits.
        *   `gates`: A list of `GateModel` objects, where each `GateModel` defines the gate's name, targets, controls (optional), and parameters (optional).
        *   `metadata`: Optional information like circuit name.
        *   `gate_counts`: A dictionary palavras-chaveing gate names to their counts.
        *   `depth`: The depth of the circuit.
    *   Gate counts and depth are calculated during the conversion from Qiskit's format.

3.  **Circuit Optimization:**
    *   The [`/circuit/optimize`](/Users/omtailor/QuantumCanvas/backend/app/routers/circuit.py) endpoint applies specified optimization passes.
    *   Optimization passes are defined in [`app/services/optimization_passes.py`](/Users/omtailor/QuantumCanvas/backend/app/services/optimization_passes.py).
    *   Currently, one pass is implemented:
        *   `remove_self_inverse_pairs`: Removes adjacent identical single-qubit gates that are their own inverse (e.g., H-H, X-X). This pass iterates through the gates and removes such pairs.
    *   The `OPTIMIZATION_PASS_REGISTRY` allows for easy addition of new optimization functions.
    *   After optimization, if gate counts or depth were invalidated (set to `None` by a pass), the circuit is converted to Qiskit and back to `CircuitJSON` to recalculate these statistics.

4.  **Circuit Conversion & Export:**
    *   The backend supports converting the internal `CircuitJSON` representation to various formats:
        *   **QASM 2.0:** The [`/circuit/export/qasm`](/Users/omtailor/QuantumCanvas/backend/app/routers/circuit.py) endpoint converts `CircuitJSON` back into an OpenQASM 2.0 string.
        *   **Pennylane Script:** The [`/circuit/export/pennylane_script`](/Users/omtailor/QuantumCanvas/backend/app/routers/circuit.py) endpoint generates a Python script string that defines the circuit as a Pennylane QNode. This conversion is handled by `circuit_json_to_pennylane_script` in [`app/utils/circuit_conversions.py`](/Users/omtailor/QuantumCanvas/backend/app/utils/circuit_conversions.py). It maps gate names to Pennylane operations and handles parameters, including string representations like "pi/2". It uses `qml.ctrl` for gates that are not natively controlled in Pennylane but have controls specified in the `CircuitJSON`.
    *   Conversion logic resides in [`app/utils/circuit_conversions.py`](/Users/omtailor/QuantumCanvas/backend/app/utils/circuit_conversions.py), which includes:
        *   `qiskit_circuit_to_json`: Qiskit `QuantumCircuit` to `CircuitJSON`.
        *   `circuit_json_to_qiskit`: `CircuitJSON` to Qiskit `QuantumCircuit`.
        *   `circuit_json_to_cirq`: `CircuitJSON` to Cirq `Circuit`.
        *   `cirq_circuit_to_json`: Cirq `Circuit` to `CircuitJSON`.
        *   `circuit_json_to_pennylane_script`: `CircuitJSON` to Pennylane script string.
    *   Gate name mapping (e.g., `QISKIT_GATE_MAP`, `CIRQT_GATE_MAP_TO_CIRQT`, `PENNYLANE_GATE_MAP`) is used to translate between the different library conventions.

### Key Libraries Used

*   **FastAPI:** For building the RESTful API.
*   **Pydantic:** For data validation and settings management (used in `app/models.py`).
*   **Qiskit:** Core library for QASM parsing, circuit manipulation, and as an intermediate for statistics calculation.
*   **Cirq & Pennylane:** For conversion to their respective formats/scripts.
*   **Uvicorn:** ASGI server to run the FastAPI application.
*   **Poetry:** For dependency management.

### Testing

*   Unit tests are located in the [`backend/tests/`](/Users/omtailor/QuantumCanvas/backend/tests) directory.
*   [`test_circuit_endpoints.py`](/Users/omtailor/QuantumCanvas/backend/tests/test_circuit_endpoints.py) tests the API endpoints for parsing, optimization, and QASM export.
*   [`test_pennylane_conversions.py`](/Users/omtailor/QuantumCanvas/backend/tests/test_pennylane_conversions.py) tests the conversion logic to Pennylane scripts, including handling of various gates, parameters, and control logic.

## Frontend Implementation (React/TypeScript/Vite)

The frontend provides a user interface to interact with the backend API.

### Core Functionality

*   **QASM Input:** Users can input OpenQASM 2.0 strings via a textarea ([`Textarea`](/Users/omtailor/QuantumCanvas/frontend/src/components/ui/textarea.tsx) component).
*   **Circuit Parsing & Display:**
    *   Sends the QASM string to the backend's `/circuit/parse` endpoint.
    *   Displays the parsed circuit details (`CircuitDetailsView` component in [`App.tsx`](/Users/omtailor/QuantumCanvas/frontend/src/App.tsx)), including qubit count, gate counts, depth, and the raw JSON of gates.
    *   Renders a visual representation of the circuit using SVG (`CircuitDiagram` component in [`App.tsx`](/Users/omtailor/QuantumCanvas/frontend/src/App.tsx)). The diagram logic calculates gate positions based on qubit availability.
*   **Circuit Optimization:**
    *   Allows users to trigger optimization (currently hardcoded to the "remove_self_inverse_pairs" pass) via a button.
    *   Sends the parsed circuit to the `/circuit/optimize` endpoint.
    *   Displays the optimized circuit details and diagram alongside the original.
*   **Export Functionality:**
    *   Buttons to export the parsed or optimized circuit to:
        *   QASM (calls `/circuit/export/qasm`).
        *   Pennylane script (calls `/circuit/export/pennylane_script`).
    *   The exported content is displayed in read-only textareas.
*   **State Management:** Uses React's `useState` hook extensively in [`App.tsx`](/Users/omtailor/QuantumCanvas/frontend/src/App.tsx) to manage QASM input, parsed/optimized circuits, exported strings, loading states, and errors.

### Key Libraries & Tools

*   **React:** For building the user interface.
*   **TypeScript:** For static typing.
*   **Vite:** For the development server and build tooling.
*   **TailwindCSS:** For utility-first styling. Configuration is in [`tailwind.config.js`](/Users/omtailor/QuantumCanvas/frontend/tailwind.config.js) and base styles/variables in [`src/index.css`](/Users/omtailor/QuantumCanvas/frontend/src/index.css).
*   **shadcn/ui components:** Uses pre-built components like [`Button`](/Users/omtailor/QuantumCanvas/frontend/src/components/ui/button.tsx), [`Textarea`](/Users/omtailor/QuantumCanvas/frontend/src/components/ui/textarea.tsx), [`Label`](/Users/omtailor/QuantumCanvas/frontend/src/components/ui/label.tsx), and [`Card`](/Users/omtailor/QuantumCanvas/frontend/src/components/ui/card.tsx) for the UI, which are styled with TailwindCSS.
*   **clsx & tailwind-merge:** Utilities for conditional class names, used in `cn` function in [`src/lib/utils.ts`](/Users/omtailor/QuantumCanvas/frontend/src/lib/utils.ts).

## Setup and Running

### Backend

1.  Navigate to the `backend` directory: `cd backend`
2.  Install dependencies using Poetry: `poetry install`
3.  Run the FastAPI development server: `poetry run uvicorn app.main:app --reload --port 8000`

### Frontend

1.  Navigate to the `frontend` directory: `cd frontend`
2.  Install dependencies: `npm install` (or `yarn install` / `pnpm install`)
3.  Run the Vite development server: `npm run dev` (usually serves on `http://localhost:5173`)

## Potential Future Work & Optimizations

*   **More Optimization Passes:** Implement a wider range of circuit optimization algorithms (e.g., gate fusion, commutation rules, template matching).
*   **QASM 3 Support:** Extend parsing capabilities to support OpenQASM 3.0 features.
*   **Advanced Circuit Visualization:** Enhance the SVG diagram with more gate types, better control visualization, and interactivity.
*   **Error Handling:** More granular error reporting from the backend to the frontend.
*   **Benchmarking:** Integrate functionality to benchmark circuits on different simulators.
*   **User-Selectable Optimization Passes:** Allow users to choose which optimization passes to apply via the UI.
*   **Improved Pennylane Script Generation:**
    *   Allow selection of different devices.
    *   Offer options for different measurement types beyond the default `qml.expval(qml.PauliZ(0))`.
    *   More robust handling of complex or custom gates during conversion.
*   **Cirq Integration in Frontend:** Allow exporting to and potentially importing from Cirq JSON or other Cirq-specific formats directly from the UI.
*   **Performance:** For very large circuits, optimize the conversion and rendering processes.