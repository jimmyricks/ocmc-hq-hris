export type TabsContext = {
  readonly value: string;
  setValue(value: string): void;
};

export const TABS_CONTEXT = Symbol("hq-tabs");
