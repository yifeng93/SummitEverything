from __future__ import annotations

import json
from pathlib import Path

from summit_everything.api.app import app
from summit_everything.domain.models import Answer, Citation

root = Path.cwd()
output = root / ".local/qa/c19-dsh-be4e72f/openapi.json"
schema = app.openapi()
components = schema.setdefault("components", {}).setdefault("schemas", {})
for model in (Citation, Answer):
    model_schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
    components.update(model_schema.pop("$defs", {}))
    components[model.__name__] = model_schema
output.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(output)
