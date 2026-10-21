export type DialogContext = {
  readonly open: boolean;
  setOpen(open: boolean): void;
};

export const DIALOG_CONTEXT = Symbol("hq-dialog");
