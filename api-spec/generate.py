import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "api-spec" / "openapi.yaml"
MODELS = ROOT / "api" / "contract_models.py"
SCHEMA = ROOT / "web" / "src" / "api" / "schema.d.ts"


def spec_sha256() -> str:
    raw = SPEC.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=ROOT)


def string_enums(spec: dict) -> dict[str, list[str]]:
    schemas = spec["components"]["schemas"]
    return {
        name: schema["enum"]
        for name, schema in schemas.items()
        if schema.get("type") == "string" and schema.get("enum")
    }


def enum_aliases(models: str, enums: dict[str, list[str]]) -> str:
    clashes = [name for name in enums if f"class {name}(" in models]
    if clashes:
        raise SystemExit(f"Enum aliases would shadow generated classes: {clashes}")
    return "\n".join(f"{name} = Literal[{', '.join(repr(value) for value in values)}]" for name, values in enums.items())


def generate_python(digest: str) -> None:
    run(
        [
            sys.executable,
            "-m",
            "datamodel_code_generator",
            "--input",
            str(SPEC),
            "--input-file-type",
            "openapi",
            "--output",
            str(MODELS),
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            "3.12",
            "--field-constraints",
            "--use-annotated",
            "--enum-field-as-literal",
            "all",
            "--collapse-root-models",
            "--disable-timestamp",
            "--use-default-kwarg",
            "--strict-nullable",
            "--encoding",
            "utf-8",
        ]
    )
    import yaml

    models = MODELS.read_text(encoding="utf-8")
    aliases = enum_aliases(models, string_enums(yaml.safe_load(SPEC.read_text(encoding="utf-8"))))
    MODELS.write_text(f"# spec-sha256: {digest}\n{models}\n\n{aliases}\n", encoding="utf-8")


def generate_typescript(digest: str) -> None:
    npx = shutil.which("npx")
    if npx is None:
        raise SystemExit("npx is not on PATH")
    SCHEMA.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            npx,
            "--prefix",
            str(ROOT / "api-spec"),
            "openapi-typescript",
            str(SPEC),
            "-o",
            str(SCHEMA),
        ]
    )
    schema = SCHEMA.read_text(encoding="utf-8")
    SCHEMA.write_text(f"// spec-sha256: {digest}\n{schema}", encoding="utf-8")


def main() -> None:
    digest = spec_sha256()
    generate_python(digest)
    generate_typescript(digest)


if __name__ == "__main__":
    main()
