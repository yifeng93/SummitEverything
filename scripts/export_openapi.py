"""Export the FastAPI contract for generated browser types."""

from __future__ import annotations

import json
from pathlib import Path

from summit_everything.api.app import app
from summit_everything.domain.models import Answer, Citation

root = Path(__file__).resolve().parents[1]
openapi_path = root / "web" / "openapi.json"
schema = app.openapi()
components = schema.setdefault("components", {}).setdefault("schemas", {})
for model in (Citation, Answer):
    model_schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
    definitions = model_schema.pop("$defs", {})
    components.update(definitions)
    components[model.__name__] = model_schema
openapi_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n")
print(f"Wrote {openapi_path.relative_to(root)}")
