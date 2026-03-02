import re

with open("webui/frontend/src/App.jsx", "r") as f:
    code = f.read()

# Make sure to import SpacePieces
if "SpacePieces" not in code:
    code = code.replace("import './App.css'\n", "import './App.css'\nimport SpacePieces from './components/SpacePieces'\n")

# Add SpacePieces rendering inside the map mapStage
replacement = """              <div className="mapOverlay">
                {state && <SpacePieces board={state.board} />}
"""
if "<SpacePieces" not in code:
    code = code.replace('              <div className="mapOverlay">\n', replacement)

with open("webui/frontend/src/App.jsx", "w") as f:
    f.write(code)
