import { useId, type InputHTMLAttributes } from "react";

type TextFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
} & Pick<InputHTMLAttributes<HTMLInputElement>, "type" | "autoComplete" | "autoCapitalize">;

export function TextField({ label, value, onChange, ...input }: TextFieldProps) {
  const id = useId();
  return (
    <div>
      <label className="field-label" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        className="field"
        spellCheck={false}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...input}
      />
    </div>
  );
}
