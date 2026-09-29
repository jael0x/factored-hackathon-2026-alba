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
    return hashlib.sha256(SPEC.read_bytes()).hexdigest()


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=ROOT)


def main() -> None:
    digest = spec_sha256()
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
    models = MODELS.read_text(encoding="utf-8")
    MODELS.write_text(f"# spec-sha256: {digest}\n{models}", encoding="utf-8")

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


if __name__ == "__main__":
    main()
