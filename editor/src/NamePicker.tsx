import { Combobox } from "@base-ui/react/combobox";
import { useId, useMemo } from "react";

export type NameOption = {
  id: string;
  label: string;
};

type Props = {
  label: string;
  options: NameOption[];
  value: string;
  onChange: (id: string) => void;
};

export function NamePicker({ label, options, value, onChange }: Props) {
  const inputId = useId();
  const listed = useMemo(() => {
    if (value && !options.some((item) => item.id === value)) {
      return [...options, { id: value, label: "Missing record" }];
    }
    return options;
  }, [options, value]);
  const items = useMemo(
    () =>
      Combobox.createItems(listed, {
        getValue: (item) => item.id,
        getLabel: (item) => item.label,
      }),
    [listed],
  );

  return (
    <Combobox.Root
      items={items}
      value={value || null}
      onValueChange={(next) => onChange(next ?? "")}
    >
      <div className="field">
        <label htmlFor={inputId}>{label}</label>
        <Combobox.InputGroup className="picker-input">
          <Combobox.Input id={inputId} placeholder="Type a name" autoComplete="off" />
          <Combobox.Clear aria-label={`Clear ${label}`} className="picker-clear pressable">
            Clear
          </Combobox.Clear>
          <Combobox.Trigger aria-label={`Open ${label}`} className="picker-trigger pressable">
            <span aria-hidden="true">▾</span>
          </Combobox.Trigger>
        </Combobox.InputGroup>
      </div>
      <Combobox.Portal>
        <Combobox.Positioner className="picker-positioner" sideOffset={4}>
          <Combobox.Popup className="picker-popup">
            <Combobox.Empty className="picker-empty">No matches</Combobox.Empty>
            <Combobox.List className="picker-list">
              {(item: NameOption) => (
                <Combobox.Item key={item.id} value={item.id} className="picker-item">
                  <span>{item.label}</span>
                </Combobox.Item>
              )}
            </Combobox.List>
          </Combobox.Popup>
        </Combobox.Positioner>
      </Combobox.Portal>
    </Combobox.Root>
  );
}
