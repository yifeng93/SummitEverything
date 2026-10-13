import json
from pathlib import Path
from summit_everything.api.app import app
from summit_everything.domain.models import Answer, Citation

output = Path(".local/qa/c19-repair-1/openapi.json")
schema = app.openapi()
components = schema.setdefault("components", {}).setdefault("schemas", {})
for model in (Citation, Answer):
    model_schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
    components.update(model_schema.pop("$defs", {}))
    components[model.__name__] = model_schema
output.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(output)
